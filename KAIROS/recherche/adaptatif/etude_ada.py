"""Étude gestion adaptative (ADA). Usage : python etude_ada.py principal | robustesse | placebo
Résultats écrits dans resultats/."""
from __future__ import annotations
import os, sys, pickle, time
import numpy as np, pandas as pd
import ada, decl
import moteur as M
import simulateur as SIM

OUT = os.path.join(ada.ICI, 'resultats')
RISQUE = 150
VARIANTE = 'tradeify_50k_select_flex'
_R = None
def regles():
    global _R
    if _R is None:
        _R = SIM.charge_regles()[VARIANTE]
    return _R

_CACHE = {}
def donnees():
    if 'S' not in _CACHE:
        S = ada.charger_dev()
        for s in S:
            s['D'] = decl.declencheurs(s['df'])
        _CACHE['S'] = S
    return _CACHE['S']

_ACACHE = {}
def A_de(s, prm):
    key = (s['nom'], tuple(sorted((prm or {}).items())))
    if key not in _ACACHE:
        _ACACHE[key] = ada.adaptatif(s['df'], prm)
    return _ACACHE[key]

def gest(s, mode, prm=None):
    """mode : 'ada' | ('fixe', R)"""
    if mode == 'ada':
        return ada.gestion_adaptative(s['df'], A_de(s, prm), s['instrument'])
    return ada.gestion_fixe(s['instrument'], mode[1])

def trades(decl_nom, mode, prm=None):
    out = []
    for s in donnees():
        if decl_nom not in s['D']:
            continue
        L, Sh = s['D'][decl_nom]
        T = M.backtest(s['df'], L, Sh, gest(s, mode, prm), details=True)
        if len(T):
            T['serie'] = s['nom']; T['decl'] = decl_nom
            if mode == 'ada':
                A = A_de(s, prm); i = T['i_signal'].to_numpy()
                T['C'] = np.where(T['sens'] == 'long', A['C_l'][i], A['C_s'][i])
                T['typ'] = np.where(T['sens'] == 'long', A['typ_l'][i], A['typ_s'][i])
            out.append(T)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()

def part_sautes(decl_nom, prm=None):
    """part des signaux (heures autorisées, ATR connu) sautés parce que obstacle < 1R."""
    tot = sk = 0
    for s in donnees():
        if decl_nom not in s['D']:
            continue
        A = A_de(s, prm); L, Sh = s['D'][decl_nom]
        idx = s['df'].index.tz_convert('Europe/Paris'); h = idx.hour
        ok = (h >= 8) & (h < 22)
        for m, suf in ((L, 'l'), (Sh, 's')):
            sel = m & ok & A['ok_' + suf]
            tot += sel.sum(); sk += (sel & np.isnan(A['stop_' + suf])).sum()
    return sk / tot if tot else np.nan

def stats(T):
    if not len(T):
        return dict(n=0, pct_gagnants=np.nan, r_moyen=np.nan, pf=np.nan)
    r = T['r'].to_numpy(float)
    g, p = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(T), pct_gagnants=100 * (r > 0).mean(), r_moyen=r.mean(), pf=g / p if p > 0 else np.inf)

def propfirm(T, n_sim=400):
    if len(T) < 5 or (np.floor(RISQUE / T['risque_usd'].astype(float)) > 0).sum() < 5:
        return dict(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, n_pris=0)
    r = SIM.monte_carlo(T, regles(), risque_usd=RISQUE, n_sim=n_sim, graine=0)
    return dict(p_reussite=r.get('p_reussite', np.nan), p_payout=r.get('p_1er_payout', np.nan),
                ve=r.get('valeur_esperee_usd', np.nan), n_pris=r.get('n_trades', 0))

def folds():
    """fenêtres de test (début, fin) des 5 plis de walk-forward, par série."""
    out = {}
    for s in donnees():
        out[s['nom']] = [(t.index[0], t.index[-1]) for _, t in M.walk_forward(s['df'], k=5, ratio=3)]
    return out

def wf(T):
    """R moyen et n par pli de test (réglages non ajustés : le walk-forward mesure la stabilité)."""
    F = folds(); res = []
    for p in range(5):
        m = np.zeros(len(T), bool)
        for nom, w in F.items():
            a, b = w[p]
            m |= ((T['serie'] == nom) & (T['entree_t'] >= a) & (T['entree_t'] <= b)).to_numpy()
        sub = T[m]
        res.append((len(sub), sub['r'].mean() if len(sub) else np.nan))
    return res

def placebo(decl_nom, prm=None, n=500, graine=1):
    """n tirages au hasard, même gestion adaptative, regroupés sur les séries. -> DataFrame (stats par tirage) + trades"""
    par_serie = []
    for k, s in enumerate(donnees()):
        if decl_nom not in s['D']:
            continue
        L, Sh = s['D'][decl_nom]
        _, trs = M.reference_hasard(s['df'], n, gest(s, 'ada', prm), graine + k, long=L, short=Sh, garder_trades=True)
        par_serie.append(trs)
    rows, tt = [], []
    for q in range(n):
        T = pd.concat([ps[q] for ps in par_serie if len(ps[q])], ignore_index=True) if par_serie else pd.DataFrame()
        rows.append(stats(T)); tt.append(T)
    return pd.DataFrame(rows), tt

def p_sup(ref, v, col):
    x = ref[col].dropna().to_numpy()
    return float((1 + (x >= v).sum()) / (1 + len(x)))

def principal(n_plac=500):
    rows = []; dist = []; wfs = []
    for d in decl.NOMS:
        t0 = time.time()
        TA = trades(d, 'ada'); TB = trades(d, ('fixe', 1.5)); TC = trades(d, ('fixe', 1.0))
        ref, tt = placebo(d, n=n_plac)
        for nom, T in (('a_adaptatif', TA), ('b_fixe_2ATR_1.5R', TB), ('c_fixe_2ATR_1R', TC)):
            st = stats(T); pf = propfirm(T)
            row = dict(entree=d, gestion=nom, **st, **pf)
            if nom.startswith('a'):
                row['sautes'] = part_sautes(d)
                row['p_hasard_r'] = p_sup(ref, st['r_moyen'], 'r_moyen')
                row['p_hasard_gagn'] = p_sup(ref, st['pct_gagnants'], 'pct_gagnants')
            rows.append(row)
            w = wf(T)
            wfs.append(dict(entree=d, gestion=nom, **{'pli%d_n' % (i + 1): w[i][0] for i in range(5)},
                            **{'pli%d_r' % (i + 1): w[i][1] for i in range(5)}))
        # placebo (d) : stats moyennes + propfirm sur 20 tirages
        pp = [propfirm(t, 200) for t in tt[:20] if len(t)]
        pr = pd.DataFrame(pp)
        rows.append(dict(entree=d, gestion='d_placebo_adaptatif', n=ref['n'].mean(), pct_gagnants=ref['pct_gagnants'].mean(),
                         r_moyen=ref['r_moyen'].mean(), pf=ref['pf'].replace(np.inf, np.nan).mean(),
                         p_reussite=pr['p_reussite'].mean() if len(pr) else np.nan,
                         p_payout=pr['p_payout'].mean() if len(pr) else np.nan, ve=pr['ve'].mean() if len(pr) else np.nan))
        if len(TA):
            dd = TA['typ'].value_counts(normalize=True).to_dict()
            dist.append(dict(entree=d, n=len(TA), **dd, **{'C%d' % c: (TA['C'] == c).mean() for c in range(4)}))
        ref.to_csv(os.path.join(OUT, 'placebo_%s.csv' % d), index=False)
        print(d, 'fini %.0fs' % (time.time() - t0), flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'principal.csv'), index=False)
    pd.DataFrame(dist).to_csv(os.path.join(OUT, 'distribution_objectifs.csv'), index=False)
    pd.DataFrame(wfs).to_csv(os.path.join(OUT, 'walk_forward.csv'), index=False)

# ───────────────────────── robustesse ─────────────────────────
def variantes():
    V = {}
    for niv in (0, 1):
        for sa in (0, 1):
            V['niv%d_sa%d' % (niv, sa)] = dict(adNiv=niv, adSaute=sa)
    for niv in (0, 1):
        b = dict(adNiv=niv, adSaute=1)
        for f in (50, 70):
            V['niv%d_feu%d' % (niv, f)] = dict(b, adFeu=f)
        for x in (20, 30):
            V['niv%d_adx%d' % (niv, x)] = dict(b, adAdx=x)
        V['niv%d_obj1-1.25-1.5' % niv] = dict(b, adR1=1.0, adR2=1.25, adR3=1.5)
        V['niv%d_sa0_obj1-1.25-1.5' % niv] = dict(b, adSaute=0, adR1=1.0, adR2=1.25, adR3=1.5)
    return V

def robustesse():
    V = variantes(); names = list(V)
    lignes = []; par = {}
    ref = {}
    for d in decl.NOMS:
        ref[d] = trades(d, ('fixe', 1.5))
    for nom in names:
        prm = V[nom]
        for d in decl.NOMS:
            T = trades(d, 'ada', prm); par[(nom, d)] = T
            st = stats(T); pf = propfirm(T, 200)
            lignes.append(dict(variante=nom, entree=d, **st, **pf, sautes=part_sautes(d, prm)))
        P = pd.concat([par[(nom, d)] for d in decl.NOMS if len(par[(nom, d)])], ignore_index=True)
        lignes.append(dict(variante=nom, entree='TOUT(5)', **stats(P), sautes=np.nan))
        print(nom, flush=True)
    R = pd.DataFrame(lignes)
    # White : écart de R par signal contre fixe 2 ATR / 1,5 R, signal sauté = 0 R ; blocs de 3 jours
    def cle(T):
        return (T['serie'] + '|' + T['decl'] + '|' + T['i_signal'].astype(str)).to_numpy()
    base = pd.concat([ref[d] for d in decl.NOMS], ignore_index=True)
    bk = cle(base); jb = pd.Series(M._jour_cme_serie(base['entree_t']).to_numpy())
    tj = sorted(set(jb)); pos = {j: i for i, j in enumerate(tj)}; nj = len(tj)
    ix_j = np.array([pos[j] for j in jb]); rb = base['r'].to_numpy(float)
    Smat = np.zeros((len(names), nj)); Nn = np.zeros(nj); np.add.at(Nn, ix_j, 1)
    for g, nom in enumerate(names):
        P = pd.concat([par[(nom, d)] for d in decl.NOMS if len(par[(nom, d)])], ignore_index=True)
        d_ = pd.Series(P['r'].to_numpy(float), index=cle(P))
        d_ = d_[~d_.index.duplicated()]
        rv = d_.reindex(bk).fillna(0.0).to_numpy()
        np.add.at(Smat[g], ix_j, rv - rb)
    obs = Smat.sum(1) / len(base)
    rng = np.random.default_rng(0); bl = 3; nb = int(np.ceil(nj / bl)); B = 3000; mx = np.empty(B)
    for b in range(B):
        deb = rng.integers(0, max(nj - bl + 1, 1), nb)
        ix = (deb[:, None] + np.arange(bl)).ravel()[:nj]
        m = Smat[:, ix].sum(1) / max(Nn[ix].sum(), 1)
        mx[b] = (m - obs).max()
    best = int(np.argmax(obs)); p = float((1 + (mx >= obs[best]).sum()) / (1 + B))
    # p individuelle (non corrigée) : contre zéro, bootstrap simple
    W = pd.DataFrame(dict(variante=names, gain_r_par_signal_vs_fixe=obs))
    W.to_csv(os.path.join(OUT, 'robustesse_white.csv'), index=False)
    R.to_csv(os.path.join(OUT, 'robustesse.csv'), index=False)
    pickle.dump(dict(meilleure=names[best], p_white=p, n_variantes=len(names), gain=obs[best]),
                open(os.path.join(OUT, 'white.pkl'), 'wb'))
    print('White : meilleure', names[best], 'gain %+.3f R/signal, p=%.3f, %d variantes' % (obs[best], p, len(names)))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    {'principal': principal, 'robustesse': robustesse}[sys.argv[1]]()
