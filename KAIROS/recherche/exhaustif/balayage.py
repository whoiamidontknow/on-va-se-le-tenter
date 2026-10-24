"""Explorateur exhaustif (EXH) : balayage par étapes des recettes déclencheur x filtres x sorties x sens x UT.

    ~/venv-quant/bin/python KAIROS/recherche/exhaustif/balayage.py            # tout (étapes 1-5)
    ~/venv-quant/bin/python KAIROS/recherche/exhaustif/balayage.py --source dataset

Étapes : (1) chaque déclencheur seul (modes suivi/inverse, sens long/short/les deux, chaque UT), gestion de
référence stop 2 ATR / objectif 2R ; (2) + 1 filtre sur les meilleures bases ; (3) + 2 puis 3 filtres ;
(4) grille de sorties sur les finalistes ; (5) contrôle du biais de sélection (White, Deflated Sharpe,
walk-forward de la PROCÉDURE de sélection) + Monte-Carlo Tradeify sur le haut du classement (finalistes.py).
Les jeux MES et NQ d'une même UT sont regroupés (micros MES / MNQ, coûts du moteur). Développement seulement.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import donnees_exh as D  # noqa: E402
import bibliotheque as B  # noqa: E402
M = D.M

N_JOURS_MIN = 12
N_MIN = 20                # trades minimum (regroupés) pour être classé
N_BOOT = 1000
K_BLOCS = 4               # blocs chronologiques par jeu (stabilité)
TOP_BASES_E2 = 30
TOP_E3 = 20
TOP_FILTRES_E3 = 8
TOP_E3B = 10
TOP_E4 = 12
SORTIE_REF = (('atr', 2.0), ('R', 2.0), 'rien')
COLS_T = ['entree_t', 'sortie_t', 'sens', 'prix_entree', 'stop_initial', 'objectif', 'prix_sortie', 'motif_sortie',
          'r', 'pnl_usd', 'risque_usd', 'mae_usd', 'mfe_usd', 'barres', 'niveau_stop', 'niveau_objectif']


# ════════════════════════════════════════════════════════════════════════════════════════
# Préparation
# ════════════════════════════════════════════════════════════════════════════════════════
class Univers:
    def __init__(self, jeux):
        self.jeux = jeux
        self.uts = sorted({j['ut'] for j in jeux})
        for j in jeux:
            df = j['df']
            j['ev'] = {k: f(df) for k, f in B.DECLENCHEURS.items()}
            j['ev'] = {k: v for k, v in j['ev'].items() if v is not None}
            j['fl'] = {}
            for k, f in B.FILTRES.items():
                try:
                    v = f(df)
                except KeyError:
                    v = None
                if v is not None:
                    j['fl'][k] = (np.asarray(v[0], bool), np.asarray(v[1], bool))
            j['g'] = {}
            jc = M._jour_cme_serie(df.index)
            uj = np.unique(jc.to_numpy())
            j['jours'] = uj
            bornes = np.linspace(0, len(uj), K_BLOCS + 1).round().astype(int)
            j['blocs'] = [set(uj[bornes[q]:bornes[q + 1]]) for q in range(K_BLOCS)]
        self.ev_noms = sorted({k for j in jeux for k in j['ev']})
        self.fl_noms = sorted({k for j in jeux for k in j['fl']})

    def jeux_ut(self, ut):
        return [j for j in self.jeux if j['ut'] == ut]

    def gestion(self, j, sortie):
        if sortie not in j['g']:
            j['g'][sortie] = B.gestion(j['df'], j['instrument'], *sortie)
        return j['g'][sortie]

    def signaux(self, j, ev, mode, sens, filtres):
        if ev not in j['ev']:
            return None
        L, S = j['ev'][ev]
        if mode == 'inverse':
            L, S = S, L
        L = L.copy(); S = S.copy()
        for f in filtres:
            if f not in j['fl']:
                return None
            okL, okS = j['fl'][f]
            L &= okL; S &= okS
        if sens == 'long':
            S[:] = False
        elif sens == 'short':
            L[:] = False
        return L, S

    def trades(self, v):
        """Trades regroupés (tous les jeux de l'UT) d'une variante."""
        out = []
        for j in self.jeux_ut(v['ut']):
            s = self.signaux(j, v['ev'], v['mode'], v['sens'], v['filtres'])
            if s is None or not (s[0].any() or s[1].any()):
                continue
            T = M.backtest(j['df'], s[0], s[1], self.gestion(j, v['sortie']))
            if len(T):
                T = T.copy(); T['jeu'] = j['nom']; T['marche'] = j['marche']
                out.append(T)
        if not out:
            return pd.DataFrame(columns=COLS_T + ['jeu', 'marche'])
        return pd.concat(out, ignore_index=True)


# ════════════════════════════════════════════════════════════════════════════════════════
# Notation
# ════════════════════════════════════════════════════════════════════════════════════════
def _jours(T):
    return M._jour_cme_serie(T['sortie_t']).to_numpy()


def boot_jour(r, jours, n_boot=N_BOOT, graine=0):
    if len(r) == 0:
        return np.array([np.nan])
    g = pd.DataFrame({'j': jours, 'r': r}).groupby('j')['r']
    s, c = g.sum().to_numpy(), g.count().to_numpy()
    rng = np.random.default_rng(graine)
    ix = rng.integers(0, len(s), size=(n_boot, len(s)))
    return s[ix].sum(1) / c[ix].sum(1)


def noter(T, U, ut):
    n = len(T)
    d = dict(n=n)
    if n == 0:
        d.update(note=-9.0)
        return d
    r = T['r'].to_numpy(float); p = T['pnl_usd'].to_numpy(float)
    j = _jours(T)
    bm = boot_jour(r, j)
    sd = r.std(ddof=1) if n > 1 else np.nan
    d.update(r_moyen=r.mean(), ic95_bas=np.percentile(bm, 2.5), ic95_haut=np.percentile(bm, 97.5),
             ic80_bas=np.percentile(bm, 10), pct_gagnants=(p > 0).mean(),
             pf=p[p > 0].sum() / -p[p < 0].sum() if (p < 0).any() else np.inf,
             t=r.mean() / (sd / math.sqrt(n)) if sd and sd > 0 else np.nan, sharpe_trade=r.mean() / sd if sd and sd > 0 else np.nan,
             net_usd=p.sum(), n_jours=len(np.unique(j)))
    for mk in ('MES', 'NQ'):
        m = T['marche'].to_numpy() == mk
        d['n_' + mk] = int(m.sum()); d['r_' + mk] = r[m].mean() if m.any() else np.nan
    # stabilité : R moyen par (jeu, bloc chronologique), cellules d'au moins 3 trades
    cel = []
    for jj in U.jeux_ut(ut):
        m = T['jeu'].to_numpy() == jj['nom']
        if not m.any():
            continue
        jm = j[m]; rm = r[m]
        for b in jj['blocs']:
            mb = np.isin(jm, list(b))
            if mb.sum() >= 3:
                cel.append(rm[mb].mean())
    d['n_cellules'] = len(cel)
    d['frac_blocs_pos'] = float(np.mean(np.array(cel) > 0)) if cel else np.nan
    d['pire_bloc'] = float(np.min(cel)) if cel else np.nan
    # NOTE ROBUSTE = borne basse IC80 du R moyen (bootstrap par jour) ; pénalités si trop peu de trades,
    # si les blocs chronologiques sont surtout négatifs ou si un marché est négatif.
    note = d['ic80_bas']
    if n < N_MIN:
        note -= 1.0
    if d['n_jours'] < N_JOURS_MIN:      # bootstrap sur trop peu de journées (ex. 5 min : ~6 jours) : non classable
        note -= 0.5
    if cel and d['frac_blocs_pos'] < 0.5:
        note -= 0.25
    if d['n_MES'] >= 8 and d['n_NQ'] >= 8 and min(d['r_MES'], d['r_NQ']) < 0:
        note -= 0.1
    d['note'] = note
    return d


_U = None
NPROC = int(os.environ.get('EXH_NPROC', '3'))


def _travail(v):
    T = _U.trades(v)
    d = noter(T, _U, v['ut'])
    if not len(T):
        return d, None, None
    comp = (_jours(T).astype('datetime64[D]').astype(np.int64), T['r'].to_numpy(float), T['jeu'].to_numpy())
    sig = hash((tuple(T['entree_t'].astype('int64')), tuple(T['sens']), tuple(np.round(T['r'].to_numpy(float), 6))))
    return d, comp, sig


def libelle(v):
    f = '+'.join(v['filtres']) if v['filtres'] else '-'
    return '%s|%s|%s|%dm|%s|%s' % (v['ev'], v['mode'], v['sens'], v['ut'], f, B.nom_sortie(*v['sortie']))


# ════════════════════════════════════════════════════════════════════════════════════════
# Balayage
# ════════════════════════════════════════════════════════════════════════════════════════
class Balayage:
    def __init__(self, U, dossier):
        self.U = U
        self.dossier = dossier
        self.lignes = []
        self.compact = {}       # id -> (jour CME de sortie (ordinal), r, jeu)
        self.vus = set()
        self.sigs = {}

    def lot(self, vs, etape):
        """Évalue une liste de variantes (en parallèle, NPROC processus) ; ignore celles déjà vues."""
        global _U
        a_faire = []
        for v in vs:
            lib = libelle(v)
            if lib not in self.vus:
                self.vus.add(lib); a_faire.append(v)
        _U = self.U
        if NPROC > 1 and len(a_faire) > 8:
            import multiprocessing as mp
            with mp.get_context('fork').Pool(NPROC) as P:
                res = P.map(_travail, a_faire, chunksize=4)
        else:
            res = [_travail(v) for v in a_faire]
        for v, (d, comp, sig) in zip(a_faire, res):
            vid = len(self.lignes)
            ligne = dict(id=vid, etape=etape, ut=v['ut'], evenement=v['ev'], mode=v['mode'], sens=v['sens'],
                         filtres='+'.join(v['filtres']), n_filtres=len(v['filtres']), sortie=B.nom_sortie(*v['sortie']),
                         stop=str(v['sortie'][0]), objectif=str(v['sortie'][1]), extra=v['sortie'][2],
                         recette=libelle(v), **d)
            ligne['doublon_de'] = self.sigs.get(sig, -1) if sig is not None else -1
            if sig is not None and sig not in self.sigs:
                self.sigs[sig] = vid
            ligne['_v'] = v
            self.lignes.append(ligne)
            if comp is not None:
                self.compact[vid] = comp

    def table(self):
        return pd.DataFrame([{k: x for k, x in l.items() if k != '_v'} for l in self.lignes])

    def sauver(self):
        t = self.table()
        t.sort_values('note', ascending=False).to_csv(os.path.join(self.dossier, 'balayage_complet.csv'), index=False,
                                                       float_format='%.4f')
        with open(os.path.join(self.dossier, 'etat_balayage.pkl'), 'wb') as fh:
            pickle.dump(dict(lignes=self.lignes, compact=self.compact), fh)
        return t

    def meilleurs(self, etape=None, k=10, n_min=N_MIN, cle=None, cap=None):
        L = [l for l in self.lignes if (etape is None or l['etape'] in etape) and l['n'] >= n_min
             and l.get('doublon_de', -1) < 0]
        L.sort(key=lambda l: -l['note'])
        out, cnt = [], {}
        for l in L:
            c = cle(l) if cle else None
            if cap and cnt.get(c, 0) >= cap:
                continue
            cnt[c] = cnt.get(c, 0) + 1
            out.append(l)
            if len(out) >= k:
                break
        return out


def etape1(BL):
    U = BL.U
    t0 = time.time()
    for ut in U.uts:
        evs = sorted({k for j in U.jeux_ut(ut) for k in j['ev']})
        BL.lot([dict(ut=ut, ev=ev, mode=mode, sens=sens, filtres=(), sortie=SORTIE_REF)
                for ev in evs for mode in ('suivi', 'inverse') for sens in ('les_deux', 'long', 'short')], 1)
    print('étape 1 : %d variantes (%.0f s)' % (len(BL.lignes), time.time() - t0), flush=True)


def etape2(BL):
    U = BL.U
    t0 = time.time()
    bases = BL.meilleurs({1}, TOP_BASES_E2, cle=lambda l: l['evenement'], cap=3)
    for b in bases:
        v0 = b['_v']
        noms = sorted({k for j in U.jeux_ut(v0['ut']) for k in j['fl']})
        BL.lot([dict(v0, filtres=(f,)) for f in noms], 2)
    print('étape 2 : %d bases, total %d variantes (%.0f s)' % (len(bases), len(BL.lignes), time.time() - t0), flush=True)
    return bases


def _cle_base(l):
    v = l['_v']
    return (v['ev'], v['mode'], v['sens'], v['ut'])


def etape3(BL):
    t0 = time.time()
    # bases de l'étape 3 : meilleures variantes à 1 filtre, au plus 2 par base
    tops = BL.meilleurs({2}, TOP_E3, cle=_cle_base, cap=2)
    faites = set()
    for l in tops:
        cb = _cle_base(l)
        if cb in faites:
            continue
        faites.add(cb)
        cand = sorted([x for x in BL.lignes if x['etape'] == 2 and _cle_base(x) == cb and x['n'] >= 10],
                      key=lambda x: -x['note'])
        fl = [x['_v']['filtres'][0] for x in cand[:TOP_FILTRES_E3]]
        v0 = l['_v']
        BL.lot([dict(v0, filtres=tuple(sorted((a, b)))) for a, b in itertools.combinations(fl, 2)], 3)
        l['_fl_top'] = fl
    print('étape 3 (2 filtres) : total %d variantes (%.0f s)' % (len(BL.lignes), time.time() - t0), flush=True)
    t0 = time.time()
    top3 = BL.meilleurs({3}, TOP_E3B, n_min=N_MIN)
    for l in top3:
        cb = _cle_base(l)
        cand = sorted([x for x in BL.lignes if x['etape'] == 2 and _cle_base(x) == cb and x['n'] >= 10],
                      key=lambda x: -x['note'])
        fl = [x['_v']['filtres'][0] for x in cand[:TOP_FILTRES_E3]]
        BL.lot([dict(l['_v'], filtres=tuple(sorted(l['_v']['filtres'] + (f,)))) for f in fl
                if f not in l['_v']['filtres']], 3)
    print('étape 3b (3 filtres) : total %d variantes (%.0f s)' % (len(BL.lignes), time.time() - t0), flush=True)


def etape4(BL):
    t0 = time.time()
    fin = BL.meilleurs({1, 2, 3}, TOP_E4, n_min=N_MIN + 10, cle=_cle_base, cap=2)
    for l in fin:
        v0 = l['_v']
        BL.lot([dict(v0, sortie=(s, o, x)) for s in B.STOPS for o in B.OBJECTIFS for x in B.EXTRAS], 4)
    print('étape 4 (sorties) : %d finalistes, total %d variantes (%.0f s)' % (len(fin), len(BL.lignes), time.time() - t0),
          flush=True)
    return fin


# ════════════════════════════════════════════════════════════════════════════════════════
# Biais de sélection
# ════════════════════════════════════════════════════════════════════════════════════════
def matrice_jour(BL, ids):
    jours = sorted({int(x) for i in ids if i in BL.compact for x in BL.compact[i][0]})
    pos = {d: k for k, d in enumerate(jours)}
    X = np.zeros((len(jours), len(ids)))
    for c, i in enumerate(ids):
        if i not in BL.compact:
            continue
        jj, r, _ = BL.compact[i]
        np.add.at(X[:, c], [pos[int(x)] for x in jj], r)
    return X, jours


def white_rc(X, n_boot=2000, bloc=5, graine=0):
    """Reality Check de White (bootstrap stationnaire par blocs de journées) sur le R journalier moyen."""
    Dn, K = X.shape
    mu = X.mean(0)
    stat = math.sqrt(Dn) * mu.max()
    rng = np.random.default_rng(graine)
    Xc = X - mu
    mx = np.empty(n_boot)
    p = 1.0 / bloc
    for b in range(n_boot):
        idx = np.empty(Dn, int); idx[0] = rng.integers(Dn)
        for t in range(1, Dn):
            idx[t] = rng.integers(Dn) if rng.random() < p else (idx[t - 1] + 1) % Dn
        mx[b] = math.sqrt(Dn) * Xc[idx].mean(0).max()
    return float((1 + (mx >= stat).sum()) / (1 + n_boot)), int(np.argmax(mu))


def deflated_sharpe(r, sr_tous, n_essais):
    from scipy.stats import norm, skew, kurtosis
    r = np.asarray(r, float)
    T = len(r)
    if T < 3 or r.std(ddof=1) == 0:
        return np.nan, np.nan
    sr = r.mean() / r.std(ddof=1)
    V = np.nanvar(sr_tous)
    g = 0.5772156649
    N = max(int(n_essais), 2)
    sr0 = math.sqrt(V) * ((1 - g) * norm.ppf(1 - 1 / N) + g * norm.ppf(1 - 1 / (N * math.e)))
    sk, ku = skew(r), kurtosis(r, fisher=False)
    den = math.sqrt(max(1 - sk * sr + (ku - 1) / 4 * sr ** 2, 1e-9))
    return float(norm.cdf((sr - sr0) * math.sqrt(T - 1) / den)), float(sr0)


def wf_procedure(BL, k=4, ratio=2, n_min_app=12):
    """Walk-forward de la PROCÉDURE de sélection (temps relatif par jeu) : chaque jeu est coupé en ratio + k blocs
    de journées ; pli p : on choisit la meilleure variante (note IC80 sur les blocs d'apprentissage), on lit son
    R moyen sur le bloc test. Mesure si « prendre le n°1 du classement » tient hors échantillon."""
    U = BL.U
    nb = ratio + k
    bloc_de = {}
    for j in U.jeux:
        uj = j['jours'].astype('datetime64[D]').astype(np.int64)
        bornes = np.linspace(0, len(uj), nb + 1).round().astype(int)
        for q in range(nb):
            for d in uj[bornes[q]:bornes[q + 1]]:
                bloc_de[(j['nom'], int(d))] = q
    res = []
    ids = [l['id'] for l in BL.lignes if l['id'] in BL.compact]
    blocs = {i: np.array([bloc_de.get((jn, int(d)), -1) for d, jn in zip(BL.compact[i][0], BL.compact[i][2])])
             for i in ids}
    for p in range(k):
        app = set(range(p, p + ratio)); tst = p + ratio
        best = []
        for i in ids:
            jj, r, _ = BL.compact[i]
            m = np.isin(blocs[i], list(app))
            if m.sum() < n_min_app:
                continue
            bm = boot_jour(r[m], jj[m], n_boot=200, graine=i)
            best.append((np.percentile(bm, 10), i))
        best.sort(reverse=True)
        def r_test(i):
            jj, r, _ = BL.compact[i]
            m = blocs[i] == tst
            return (r[m].mean() if m.any() else np.nan), int(m.sum())
        top1 = r_test(best[0][1]) if best else (np.nan, 0)
        top10 = [r_test(i) for _, i in best[:10]]
        tous = [r_test(i) for _, i in best]
        res.append(dict(pli=p, n_candidats=len(best), choisi=BL.lignes[best[0][1]]['recette'] if best else '',
                        note_app=best[0][0] if best else np.nan, r_test_n1=top1[0], n_test_n1=top1[1],
                        r_test_top10=np.nanmean([x[0] for x in top10]) if top10 else np.nan,
                        r_test_tous=np.nanmean([x[0] for x in tous]) if tous else np.nan))
    return pd.DataFrame(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    ap.add_argument('--recalcul', action='store_true')
    ap.add_argument('--jusqua', type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    jeux = D.charger_jeux(a.source, recalcul=a.recalcul)
    print('jeux : %s (%.0f s)' % (', '.join('%s:%d' % (j['nom'], len(j['df'])) for j in jeux), time.time() - t0), flush=True)
    U = Univers(jeux)
    BL = Balayage(U, ICI)
    etape1(BL); BL.sauver()
    if a.jusqua >= 2:
        etape2(BL); BL.sauver()
    if a.jusqua >= 3:
        etape3(BL); BL.sauver()
    if a.jusqua >= 4:
        etape4(BL); BL.sauver()
    # biais de sélection
    t = BL.table()
    ok = [l['id'] for l in BL.lignes if l['n'] >= N_MIN and l['id'] in BL.compact]
    X, _ = matrice_jour(BL, ok)
    p_white, kbest = white_rc(X)
    sr_tous = np.array([BL.lignes[i]['sharpe_trade'] for i in ok], float)
    top = BL.meilleurs(None, 20)
    dsr = {}
    for l in top:
        dsr[l['id']] = deflated_sharpe(BL.compact[l['id']][1], sr_tous, len(BL.lignes))
    wf = wf_procedure(BL)
    wf.to_csv(os.path.join(ICI, 'wf_procedure.csv'), index=False, float_format='%.4f')
    meta = dict(n_variantes=len(BL.lignes), n_classees=len(ok), p_white=p_white,
                meilleur_white=BL.lignes[ok[kbest]]['recette'], dsr={int(k): v for k, v in dsr.items()},
                duree_s=time.time() - t0, source=a.source or D.SOURCE)
    with open(os.path.join(ICI, 'meta_balayage.json'), 'w') as fh:
        json.dump(meta, fh, indent=1, default=float)
    print(json.dumps({k: v for k, v in meta.items() if k != 'dsr'}, indent=1, default=float))
    print(wf.to_string())


if __name__ == '__main__':
    main()
