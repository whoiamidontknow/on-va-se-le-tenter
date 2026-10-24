"""Le taux de gagnants aide-t-il en propfirm ? Pour quelques entrées et des gestions qui parcourent la frontière
(37 % -> 76 % de gagnants), Tradeify Select Flex : taille en micros optimisée (optimise_taille, valeur espérée)
pour les trades réels, et MÊME taille pour 20 tirages au hasard de même gestion (moteur.reference_hasard).
Échantillon : développement complet (EN échantillon : sert à comprendre l'effet de la géométrie, pas à valider).
    ~/venv-quant/bin/python propfirm_frontiere.py   -> resultats/propfirm_frontiere.csv
"""
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import etude_wrs as W

DECLS = ['ML-0001', 'hasard', 'A_clx_trend', 'hei', 'sigF']
GEST = [(2.0, 'hei'), (2.0, 'R2'), (2.0, 'BE1t4+hei'), (2.0, 'R1'), (2.0, 'BE0.5t4+hei'), (3.0, 'BE0.5t4+R2'),
        (2.0, 'P0.5+heure'), (2.0, 'P0.5+tr3'), (3.0, 'R0.5'), (2.0, 'P0.3+tr3'), (2.0, 'R0.3')]


def _tache(args):
    d, (k, so) = args
    ut, pk = W.DECLS[d]
    reels, tir = [], [[] for _ in range(20)]
    for P in W.DW.charger(ut):
        if d not in P['decl']:
            continue
        L, S = P['decl'][d]
        g = W.gestion(P, k, so, W.PLAGES[pk])
        T = W.M.backtest(P['df'], L, S, g)
        if len(T):
            reels.append(T)
        _, trs = W.M.reference_hasard(P['df'], 20, g, graine=21, long=L, short=S, garder_trades=True)
        for q, t in enumerate(trs):
            if len(t):
                tir[q].append(t)
    T = pd.concat(reels, ignore_index=True)
    tir = [pd.concat(t, ignore_index=True) for t in tir if t]
    R = W.regles()
    tab, best = W.SIM.optimise_taille(T, R, tailles=range(1, 16), n_sim=500, graine=1)
    c = int(best['contrats'])
    ref = W.SIM.analyse_reference(tir, R, contrats=c, n_sim=20 * 300)
    m = W.M.metriques(T, n_boot=1)
    return dict(decl=d, stop=k, sortie=so, n=m['n'], win=m['pct_gagnants'], r=m['r_moyen'],
                win_hasard=float(np.mean([(t['pnl_usd'] > 0).mean() for t in tir])),
                r_hasard=float(np.mean([t['r'].mean() for t in tir])), micros=c, p=best['p_reussite'],
                p1=best['p_1er_payout'], ve=best['valeur_esperee_usd'], delai=best.get('delai_median_jours'),
                p_hasard=ref.get('p_reussite'), p1_hasard=ref.get('p_1er_payout'), ve_hasard=ref.get('valeur_esperee_usd'))


if __name__ == '__main__':
    taches = [(d, g) for d in DECLS for g in GEST]
    with ProcessPoolExecutor(max_workers=9) as ex:
        rows = list(ex.map(_tache, taches))
    F = pd.DataFrame(rows)
    F.to_csv(os.path.join(W.OUT, 'propfirm_frontiere.csv'), index=False)
    pd.set_option('display.width', 250)
    print(F.round(3).to_string())
