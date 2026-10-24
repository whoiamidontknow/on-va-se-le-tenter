"""Étape 2 : walk-forward, correction du biais de sélection, placebo de même géométrie, simulateur Tradeify.

    ~/venv-quant/bin/python analyse.py wf          # walk-forward des procédures de choix -> resultats/wf_*.csv
    ~/venv-quant/bin/python analyse.py white       # bootstrap de White (Reality Check + version studentisée)
    ~/venv-quant/bin/python analyse.py finalistes  # placebo 500 tirages + simulateur pour les recettes retenues

PLACEBO DE MÊME GÉOMÉTRIE : mêmes séries, mêmes sens, même heure Paris et même nombre de signaux
(moteur.reference_hasard), même gestion (sortie temporelle, 15:59 Chicago, coûts). Le stop et l'objectif de
chaque entrée au hasard sont tirés dans la distribution des distances (en ATR) des VRAIS trades de la recette
(paires stop / objectif tirées ensemble) : le placebo a donc la même géométrie stop / objectif, seule l'entrée
change. Pour un objectif en R, seul le stop est tiré et l'objectif reste k × le risque.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import donnees_wrf as D  # noqa: E402
import setups as ST  # noqa: E402
import moteur as M  # noqa: E402
import simulateur as SIM  # noqa: E402

OUT = os.path.join(ICI, 'resultats')
REGLE = 'tradeify_50k_select_flex'
TAILLES = [1, 2, 3, 4, 5, 6, 8, 10]
N_MIN_APP = 20                 # trades minimum en apprentissage pour qu'une variante soit éligible
BANDE = (0.60, 0.75)
K_PLIS, RATIO = 5, 3


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def charger():
    B = pd.read_csv(os.path.join(OUT, 'balayage.csv'))
    T = pickle.load(open(os.path.join(OUT, 'trades_balayage.pkl'), 'rb'))
    return B, T


def stats(T):
    if T is None or not len(T):
        return dict(n=0, pct_gagnants=np.nan, r_moyen=np.nan, pf=np.nan)
    g, p = T.loc[T['pnl_usd'] > 0, 'pnl_usd'].sum(), -T.loc[T['pnl_usd'] < 0, 'pnl_usd'].sum()
    return dict(n=len(T), pct_gagnants=float((T['pnl_usd'] > 0).mean()), r_moyen=float(T['r'].mean()),
                pf=float(g / p) if p > 0 else np.nan)


# ──────────────────────────────────────────────── plis walk-forward (par série, blocs de journées CME)
def blocs_par_serie(series):
    """{serie: {jour_cme: n° de bloc}} : chaque série est coupée en RATIO + K_PLIS blocs de journées."""
    out = {}
    for s in series:
        uj = np.unique(D.jour_cme(s['df'].index))
        nb = RATIO + K_PLIS
        bornes = np.linspace(0, len(uj), nb + 1).round().astype(int)
        out[s['nom']] = {j: q for q in range(nb) for j in uj[bornes[q]:bornes[q + 1]]}
    return out


def bloc_trades(T, blocs):
    j = D.jour_cme(pd.DatetimeIndex(T['entree_t']))
    return np.array([blocs[s].get(x, -1) for s, x in zip(T['serie'], j)])


def wf_procedure(B, TR, blocs, candidats, critere='r_moyen'):
    """Pour chaque pli : choisit la variante sur l'apprentissage (blocs p..p+RATIO-1 de chaque série) parmi
    `candidats` (n >= N_MIN_APP, % gagnants dans la BANDE, R moyen > 0) en maximisant `critere`, puis garde
    ses trades du bloc de test p+RATIO. -> (trades hors échantillon concaténés, choix par pli)."""
    cache = {v: bloc_trades(TR[v], blocs) for v in candidats if TR.get(v) is not None and len(TR[v])}
    oos, choix = [], []
    for p in range(K_PLIS):
        app = set(range(p, p + RATIO)); test = p + RATIO
        best, bv = None, -np.inf
        for v, bl in cache.items():
            t = TR[v][np.isin(bl, list(app))]
            if len(t) < N_MIN_APP:
                continue
            st = stats(t)
            if not (BANDE[0] <= st['pct_gagnants'] <= BANDE[1]) or st['r_moyen'] <= 0:
                continue
            if st[critere] > bv:
                best, bv = v, st[critere]
        if best is None:
            choix.append(dict(pli=p, variante=None)); continue
        t = TR[best][cache[best] == test].copy(); t['pli'] = p; t['variante'] = best
        oos.append(t)
        choix.append(dict(pli=p, variante=best, r_app=bv, **{k + '_test': v for k, v in stats(t).items()}))
    O = pd.concat(oos, ignore_index=True).sort_values('entree_t').reset_index(drop=True) if oos else None
    return O, pd.DataFrame(choix)


def etape_wf():
    B, TR = charger()
    series = D.charger_series()
    blocs = blocs_par_serie(series)
    toutes = list(B['variante'])
    scopes = {'global': toutes}
    for fam in B['famille'].unique():
        scopes[fam] = list(B.loc[B['famille'] == fam, 'variante'])
    for setup in B['setup'].unique():
        scopes['setup:' + setup] = list(B.loc[B['setup'] == setup, 'variante'])
    lignes, oos_all = [], {}
    for nom, cand in scopes.items():
        O, C = wf_procedure(B, TR, blocs, cand)
        st = stats(O)
        lignes.append(dict(procedure=nom, n_candidats=len(cand), **st,
                           plis_sans_choix=int(C['variante'].isna().sum()),
                           choix=' ; '.join(str(x) for x in C['variante'])))
        oos_all[nom] = (O, C)
    W = pd.DataFrame(lignes).sort_values('r_moyen', ascending=False)
    W.to_csv(os.path.join(OUT, 'wf_procedures.csv'), index=False)
    pickle.dump(oos_all, open(os.path.join(OUT, 'wf_oos.pkl'), 'wb'))
    pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 120)
    print(W[['procedure', 'n_candidats', 'n', 'pct_gagnants', 'r_moyen', 'pf', 'plis_sans_choix']].round(3).to_string())


# ──────────────────────────────────────────────── White Reality Check (bootstrap stationnaire)
def _stationnaire(T, nb, bloc, rng):
    p = 1.0 / bloc
    idx = np.empty((nb, T), int)
    idx[:, 0] = rng.integers(T, size=nb)
    nouveau = rng.random((nb, T)) < p
    alea = rng.integers(T, size=(nb, T))
    for t in range(1, T):
        idx[:, t] = np.where(nouveau[:, t], alea[:, t], (idx[:, t - 1] + 1) % T)
    return idx


def etape_white(n_boot=2000, bloc=5, n_min=30):
    B, TR = charger()
    vs = [v for v in B['variante'] if TR.get(v) is not None and len(TR[v]) >= n_min]
    jours = sorted(set(np.concatenate([D.jour_cme(pd.DatetimeIndex(TR[v]['entree_t'])) for v in vs])))
    # toutes les journées de cotation des séries (journées sans trade = 0)
    series = D.charger_series()
    jours = np.array(sorted(set(np.concatenate([np.unique(D.jour_cme(s['df'].index)) for s in series]))))
    pos = {j: k for k, j in enumerate(jours)}
    X = np.zeros((len(jours), len(vs)))
    for k, v in enumerate(vs):
        t = TR[v]
        jj = D.jour_cme(pd.DatetimeIndex(t['entree_t']))
        np.add.at(X[:, k], [pos[j] for j in jj], t['r'].to_numpy(float))
    T = len(jours)
    mu = X.mean(0); sd = X.std(0, ddof=1); sd[sd == 0] = np.inf
    rng = np.random.default_rng(11)
    idx = _stationnaire(T, n_boot, bloc, rng)
    stat_rc = np.sqrt(T) * mu.max(); stat_spa = (np.sqrt(T) * mu / sd).max()
    Xc = X - mu
    mb_rc = np.empty(n_boot); mb_spa = np.empty(n_boot)
    for b in range(n_boot):
        m = Xc[idx[b]].mean(0)
        mb_rc[b] = np.sqrt(T) * m.max(); mb_spa[b] = (np.sqrt(T) * m / sd).max()
    res = dict(n_variantes=len(vs), n_jours=T, meilleure_rc=vs[int(mu.argmax())],
               meilleure_t=vs[int((mu / sd).argmax())], p_white_rc=float((mb_rc >= stat_rc).mean()),
               p_white_studentise=float((mb_spa >= stat_spa).mean()))
    # p-value corrigée de chaque variante du top 20 (studentisé, méthode « max » en une étape)
    tk = np.sqrt(T) * mu / sd
    top = np.argsort(-tk)[:20]
    res['top20'] = [dict(variante=vs[k], r_jour=float(mu[k]), t=float(tk[k]),
                         p_corrigee=float((mb_spa >= tk[k]).mean())) for k in top]
    json.dump(res, open(os.path.join(OUT, 'white.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'top20'}, indent=1))
    for r in res['top20'][:10]:
        print(r)


# ──────────────────────────────────────────────── placebo de même géométrie
def parse(v):
    setup, stop, cible, temps = v.split('|')
    fn = {c: f for c, _, f in ST.catalogue()}[setup]
    return fn, stop, cible, int(temps[1:])


def geometrie(T, df):
    """distances stop / objectif (en ATR du moteur à la barre signal) des vrais trades d'une série."""
    a = df['atr'].to_numpy(float)[T['i_signal'].to_numpy(int)]
    s = np.abs(T['prix_entree'] - T['stop_initial']).to_numpy(float) / a
    t = np.abs(T['objectif'] - T['prix_entree']).to_numpy(float) / a
    return s, t


def placebo(v, TR_v, series, n_tirages=500, jours=None, graine=0):
    """-> (DataFrame par tirage : n, pct_gagnants, r_moyen, pf ; liste des trades par tirage).
    jours : {serie: ensemble de journées CME} pour restreindre (walk-forward)."""
    fn, stop, cible, temps = parse(v)
    en_R = cible.startswith('R')
    geo = []
    for s in series:
        t = TR_v[TR_v['serie'] == s['nom']]
        if len(t):
            g = geometrie(t, s['df']); geo.append(np.column_stack(g))
    geo = np.vstack(geo)
    geo = geo[np.isfinite(geo[:, 0]) & (geo[:, 0] > 0) & (en_R | np.isfinite(geo[:, 1]))]
    rng = np.random.default_rng(graine)
    prep = []
    for s in series:
        df = s['df']
        L, S = ST.signaux(df, s['instrument'], fn)
        if jours is not None:
            m = np.isin(D.jour_cme(df.index), list(jours.get(s['nom'], ())))
            if not m.any():
                continue
            df, L, S = df[m], L[m], S[m]
        if not (L.any() or S.any()):
            continue
        prep.append((s, df, L, S))
    par_tirage, lignes = [], []
    for k in range(n_tirages):
        morceaux = []
        for q, (s, df, L, S) in enumerate(prep):
            n = len(df); c = df['c'].to_numpy(float); a = df['atr'].to_numpy(float)
            g = geo[rng.integers(len(geo), size=n)]
            G = dict(instrument=s['instrument'], heure_sortie='15:59', max_trades_jour=0, sortie_barres=temps,
                     stop=dict(mode='niveau', long=c - g[:, 0] * a, short=c + g[:, 0] * a, marge_ticks=0,
                               min_atr=None, max_atr=None, sauter=True))
            if en_R:
                G['objectif'] = dict(mode='R', k=float(cible[1:]))
            else:
                G['objectif'] = dict(mode='niveau', long=c + g[:, 1] * a, short=c - g[:, 1] * a, ratio_min=0.0,
                                     si_absent='sauter')
            _, trs = M.reference_hasard(df, 1, G, graine=int(rng.integers(1 << 30)), long=L, short=S,
                                        garder_trades=True)
            if len(trs[0]):
                t = trs[0].copy(); t['serie'] = s['nom']; t['instrument'] = s['instrument']; morceaux.append(t)
        T = pd.concat(morceaux, ignore_index=True).sort_values('entree_t').reset_index(drop=True) if morceaux \
            else pd.DataFrame(columns=M.COLONNES_TRADES)
        par_tirage.append(T)
        lignes.append(stats(T))
    return pd.DataFrame(lignes), par_tirage


def comparer(T, P):
    st = stats(T)
    return dict(**st, pct_placebo=float(P['pct_gagnants'].mean()), r_placebo=float(P['r_moyen'].mean()),
                ecart_pts=100 * (st['pct_gagnants'] - P['pct_gagnants'].mean()),
                p_taux=float((1 + (P['pct_gagnants'] >= st['pct_gagnants']).sum()) / (1 + len(P))),
                p_r=float((1 + (P['r_moyen'] >= st['r_moyen']).sum()) / (1 + len(P))), n_tirages=len(P))


def simulateur(T, refs, regles, n_sim=1000):
    tab, best = SIM.optimise_taille(T, regles, TAILLES, n_sim=n_sim, ordre='prudent', bloc_jours=5)
    c = int(best['contrats'])
    ref = SIM.analyse_reference(refs[:40], regles, c, n_sim=n_sim, ordre='prudent', bloc_jours=5)
    return dict(contrats=c, p_reussite=best.get('p_reussite'), p_1er_payout=best.get('p_1er_payout'),
                ve_usd=best.get('valeur_esperee_usd'), ref_p_reussite=ref.get('p_reussite'),
                ref_p_1er_payout=ref.get('p_1er_payout'), ref_ve_usd=ref.get('valeur_esperee_usd'))


def placebo_wf(O, C, TR, series, blocs, n_tirages=500):
    """placebo de la procédure walk-forward : pour chaque pli, la variante choisie, sur les journées de test."""
    par = [None] * n_tirages
    for _, ch in C.iterrows():
        if not isinstance(ch['variante'], str):
            continue
        test = int(ch['pli']) + RATIO
        jours = {s: {j for j, q in b.items() if q == test} for s, b in blocs.items()}
        _, trs = placebo(ch['variante'], TR[ch['variante']], series, n_tirages, jours, graine=int(ch['pli']))
        for k, t in enumerate(trs):
            par[k] = t if par[k] is None else pd.concat([par[k], t], ignore_index=True)
    par = [p.sort_values('entree_t').reset_index(drop=True) for p in par]
    return pd.DataFrame([stats(p) for p in par]), par


FINALISTES = []      # rempli après lecture du walk-forward (voir RESULTATS.md)


def etape_finalistes(variantes, n_tirages=500, procedures=()):
    B, TR = charger()
    series = D.charger_series()
    blocs = blocs_par_serie(series)
    regles = SIM.charge_regles()[REGLE]
    out = []
    for v in variantes:
        T = TR[v]
        P, refs = placebo(v, T, series, n_tirages)
        cmp_ = comparer(T, P)
        nuit = T['entree_t'].dt.tz_convert('Europe/Paris').dt.hour < 8
        sim = simulateur(T, refs, regles)
        ligne = dict(objet='recette', nom=v, **cmp_, **sim,
                     r_nuit=float(T.loc[nuit, 'r'].mean()), n_nuit=int(nuit.sum()),
                     r_jour=float(T.loc[~nuit, 'r'].mean()), n_jour=int((~nuit).sum()))
        out.append(ligne); log(ligne)
        T.to_csv(os.path.join(OUT, 'trades_%s.csv' % v.replace('|', '_')), index=False)
    oos = pickle.load(open(os.path.join(OUT, 'wf_oos.pkl'), 'rb'))
    for proc in procedures:
        O, C = oos[proc]
        if O is None or not len(O):
            continue
        P, refs = placebo_wf(O, C, TR, series, blocs, n_tirages)
        sim = simulateur(O, refs, regles)
        ligne = dict(objet='walk-forward', nom=proc, **comparer(O, P), **sim)
        out.append(ligne); log(ligne)
        O.to_csv(os.path.join(OUT, 'trades_wf_%s.csv' % proc.replace(':', '_').replace(' ', '_')), index=False)
    R = pd.DataFrame(out)
    f = os.path.join(OUT, 'finalistes.csv')
    if os.path.exists(f):
        R = pd.concat([pd.read_csv(f), R]).drop_duplicates(['objet', 'nom'], keep='last')
    R.to_csv(f, index=False)


if __name__ == '__main__':
    etape = sys.argv[1] if len(sys.argv) > 1 else 'wf'
    if etape == 'wf':
        etape_wf()
    elif etape == 'white':
        etape_white()
    elif etape == 'finalistes':
        vs = [a for a in sys.argv[2:] if '|' in a]
        procs = [a[5:] for a in sys.argv[2:] if a.startswith('proc=')]
        etape_finalistes(vs, procedures=procs)


# ──────────────────────────────────────────────── contrôles des finalistes
def p_white_variantes(variantes, n_boot=2000, bloc=5, n_min=30):
    """p-value corrigée (max studentisé sur TOUT le balayage, bootstrap stationnaire) de chaque variante."""
    B, TR = charger()
    vs = [v for v in B['variante'] if TR.get(v) is not None and len(TR[v]) >= n_min]
    series = D.charger_series()
    jours = np.array(sorted(set(np.concatenate([np.unique(D.jour_cme(s['df'].index)) for s in series]))))
    pos = {j: k for k, j in enumerate(jours)}
    X = np.zeros((len(jours), len(vs)))
    for k, v in enumerate(vs):
        jj = D.jour_cme(pd.DatetimeIndex(TR[v]['entree_t']))
        np.add.at(X[:, k], [pos[j] for j in jj], TR[v]['r'].to_numpy(float))
    T = len(jours); mu = X.mean(0); sd = X.std(0, ddof=1); sd[sd == 0] = np.inf
    idx = _stationnaire(T, n_boot, bloc, np.random.default_rng(11))
    Xc = X - mu
    mb = np.array([(np.sqrt(T) * Xc[i].mean(0) / sd).max() for i in idx])
    out = {}
    for v in variantes:
        k = vs.index(v); t = np.sqrt(T) * mu[k] / sd[k]
        out[v] = dict(t=float(t), p_brute=float(np.mean([(np.sqrt(T) * Xc[i, k].mean() / sd[k]) >= t for i in idx])),
                      p_white=float((mb >= t).mean()), n_variantes=len(vs))
    return out


def df_causal(df):
    """exécution sur la reconstitution CAUSALE (contrôle : le lissage avant-arrière ne doit pas créer l'avantage)."""
    d = df.copy()
    for k in ('o', 'h', 'l', 'c', 'atr'):
        if k + '_causal' in d.columns:
            d[k] = d[k + '_causal']
    return d


def controles(variantes):
    B, TR = charger()
    series = D.charger_series()
    blocs = blocs_par_serie(series)
    pw = p_white_variantes(variantes)
    lignes = []
    for v in variantes:
        T = TR[v]
        fn, stop, cible, temps = parse(v)
        # exécution causale
        mc = []
        for s in series:
            dfc = df_causal(s['df'])
            L, S = ST.signaux(s['df'], s['instrument'], fn)
            t = M.backtest(dfc, long=L, short=S, gestion=ST.gestion(dfc, s['instrument'], stop, cible, temps))
            if len(t):
                mc.append(t)
        C = pd.concat(mc) if mc else None
        bl = bloc_trades(T, blocs)
        par_serie = {s: stats(T[T['serie'] == s]) for s in T['serie'].unique()}
        par_bloc = [stats(T[bl == q]) for q in range(RATIO + K_PLIS)]
        lignes.append(dict(variante=v, **pw[v], **{'causal_' + k: x for k, x in stats(C).items()},
                           series=' ; '.join('%s n=%d %.0f%% %+.2fR' % (s, x['n'], 100 * x['pct_gagnants'], x['r_moyen'])
                                             for s, x in par_serie.items()),
                           blocs=' ; '.join('%d:%d/%.0f%%/%+.2f' % (q, x['n'], 100 * (x['pct_gagnants'] if x['n'] else 0),
                                                                     x['r_moyen'] if x['n'] else 0)
                                            for q, x in enumerate(par_bloc)),
                           long=stats(T[T['sens'] == 'long'])['r_moyen'], short=stats(T[T['sens'] == 'short'])['r_moyen'],
                           n_long=int((T['sens'] == 'long').sum())))
    R = pd.DataFrame(lignes)
    R.to_csv(os.path.join(OUT, 'controles_finalistes.csv'), index=False)
    return R
