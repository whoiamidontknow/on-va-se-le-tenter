"""Test PRÉ-ENREGISTRÉ H-NUIT (voir RESULTATS.md §1) : nuit 00:00-08:00 Paris contre le reste, tous
déclencheurs, gestions A15R2 puis A15R1. Aucune réoptimisation.

    ~/venv-quant/bin/python test_nuit.py [--source dataset] [--n 1000]

Sorties : sorties/test_nuit.csv (une ligne par gestion × fenêtre × série), sorties/test_nuit.json,
sorties/trades_nuit_<gestion>_<fenetre>.csv.
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import commun as C
import moteur as M

ICI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ICI, 'sorties')


def wr(T):
    return float((T['pnl_usd'] > 0).mean()) if len(T) else np.nan


def boot_delta(Tn, Tr, n=10000, graine=0):
    """Écart de R moyen nuit − reste ; bootstrap par journée CME (indépendant dans chaque groupe)."""
    rng = np.random.default_rng(graine)
    out = []
    for T in (Tn, Tr):
        j = C.jour_cme_trades(T)
        g = pd.DataFrame(dict(j=j, r=T['r'].to_numpy())).groupby('j')['r']
        s, c = g.sum().to_numpy(), g.count().to_numpy()
        ix = rng.integers(0, len(s), size=(n, len(s)))
        out.append(s[ix].sum(1) / c[ix].sum(1))
    d = out[0] - out[1]
    obs = Tn['r'].mean() - Tr['r'].mean()
    return float(obs), (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))), float((d <= 0).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    ap.add_argument('--n', type=int, default=1000)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    PP = [C.preparer(s) for s in C.charger_series(a.source)]
    lignes, res = [], {}
    for geom in ('A15R2', 'A15R1'):
        TT, REF = {}, {}
        for fen in ('nuit', 'reste'):
            trs, refs = [], [[] for _ in range(a.n)]
            for q, P in enumerate(PP):
                X = P['X']
                m = (X['seance'].to_numpy() == 0) if fen == 'nuit' else (X['seance'].to_numpy() != 0)
                G = C.gestion(geom, P['instrument'])
                T = C.backtest_masque(P, G, m, m)
                trs.append(T)
                t0 = time.time()
                pl = C.placebo(P, G, m, m, a.n, graine=100 * q + (fen == 'nuit'))
                for k, t in enumerate(pl):
                    refs[k].append(t)
                mm = M.metriques(T, n_boot=200) if len(T) else dict(n=0)
                wr_pl = np.array([wr(t) for t in pl]); r_pl = np.array([t['r'].mean() if len(t) else np.nan for t in pl])
                lignes.append(dict(gestion=geom, fenetre=fen, serie=P['nom'], n=len(T), pct_gagnants=wr(T),
                                   pct_gagnants_placebo=float(np.nanmean(wr_pl)), r_moyen=mm.get('r_moyen'),
                                   r_placebo=float(np.nanmean(r_pl)), pf=mm.get('pf'),
                                   p_r=float((1 + (r_pl >= mm.get('r_moyen', np.inf)).sum()) / (1 + len(r_pl))),
                                   p_taux=float((1 + (wr_pl >= wr(T)).sum()) / (1 + len(wr_pl)))))
                print(time.strftime('%H:%M:%S'), geom, fen, P['nom'], len(T), '%.0fs' % (time.time() - t0), flush=True)
            T = pd.concat(trs).sort_values('entree_t').reset_index(drop=True)
            refs = [pd.concat(x).sort_values('entree_t').reset_index(drop=True) for x in refs]
            TT[fen], REF[fen] = T, refs
            mm = M.metriques(T)
            wr_pl = np.array([wr(t) for t in refs]); r_pl = np.array([t['r'].mean() for t in refs])
            L = dict(gestion=geom, fenetre=fen, serie='TOUTES', n=mm['n'], pct_gagnants=mm['pct_gagnants'],
                     pct_gagnants_placebo=float(wr_pl.mean()), r_moyen=mm['r_moyen'], r_ic95=mm['r_ic95'],
                     r_placebo=float(r_pl.mean()), pf=mm['pf'], net_usd=mm['gain_net_usd'],
                     p_r=float((1 + (r_pl >= mm['r_moyen']).sum()) / (1 + len(r_pl))),
                     p_taux=float((1 + (wr_pl >= mm['pct_gagnants']).sum()) / (1 + len(wr_pl))))
            L.update({k: v for k, v in C.simuler(T, refs).items()})
            lignes.append(L)
            T.to_csv(os.path.join(OUT, 'trades_nuit_%s_%s.csv' % (geom, fen)), index=False)
            pd.concat([C.compact(t, k) for k, t in enumerate(refs)]).to_pickle(
                os.path.join(OUT, 'placebo_nuit_%s_%s.pkl' % (geom, fen)))
            print(geom, fen, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in L.items()}, flush=True)
        d, ic, p = boot_delta(TT['nuit'], TT['reste'])
        res[geom] = dict(delta_r=d, ic95=ic, p_unilateral=p)
        print(geom, 'delta nuit - reste', res[geom], flush=True)
        pd.DataFrame(lignes).to_csv(os.path.join(OUT, 'test_nuit.csv'), index=False)
    # décision pré-enregistrée
    tab = pd.DataFrame(lignes)
    ok = True
    for geom in ('A15R2', 'A15R1'):
        n = tab[(tab.gestion == geom) & (tab.fenetre == 'nuit') & (tab.serie == 'TOUTES')].iloc[0]
        ok &= res[geom]['delta_r'] > 0 and res[geom]['p_unilateral'] < 0.05 and n['p_r'] < 0.05
    res['decision'] = 'H-NUIT confirmée sur le cache' if ok else 'H-NUIT non confirmée'
    json.dump(res, open(os.path.join(OUT, 'test_nuit.json'), 'w'), indent=1, default=str)
    print(res)


if __name__ == '__main__':
    main()
