"""Étape 4 : contrôles complémentaires (tous DÉCLARÉS ici et rapportés, aucun choisi après coup).

1. Sensibilité du walk-forward de la procédure : n minimum à l'apprentissage 25 (principal) / 50 / 80, et
   classement par z d'écart de taux (principal) ou par borne basse de l'écart (écart - 1 écart-type).
2. Hors échantillon de TOUTES les variantes éligibles à l'apprentissage (pas seulement la 1re).
3. Déclencheurs seuls (sans filtre) : écart de taux par bloc chronologique (stabilité).
4. Hypothèse FIXÉE À L'AVANCE « la nuit 0 h-8 h Paris est meilleure » : pour chaque déclencheur × sens × UT ×
   géométrie sans autre filtre, écart de taux et R des trades de nuit contre les autres (mêmes tables, placebo de
   même heure) ; on rapporte la part des cas où la nuit fait mieux et l'écart médian. Aucun réglage choisi.
Écrit sorties/complements_<source>.pkl et sorties/complements.txt.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import analyse as AN  # noqa: E402
import balayage as BA  # noqa: E402
import bib_wrx as B  # noqa: E402
import donnees_wrx as D  # noqa: E402
import tables as TB  # noqa: E402


def wf(BL, n_min, critere):
    tests = []
    choix = []
    for p in range(AN.K_PLIS):
        Str = AN.stats_blocs(BL, list(range(p, p + AN.RATIO)))
        Ste = AN.stats_blocs(BL, [p + AN.RATIO])
        cand = np.flatnonzero(AN.eligible(Str, n_min))
        if not len(cand):
            continue
        if critere == 'z':
            sc = Str['z_ecart'].to_numpy()
        else:   # borne basse : écart - 1 écart-type (binomial, placebo)
            n = Str['n'].to_numpy(); tx = Str['taux'].to_numpy()
            sc = (tx - Str['taux_placebo'].to_numpy()) - np.sqrt(np.maximum(tx * (1 - tx), 1e-9) / np.maximum(n, 1))
        k = cand[np.argmax(sc[cand])]
        tests.append(Ste.iloc[k].to_dict()); choix.append(k)
    return AN.agreger(tests) if tests else {}, choix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=D.SOURCE)
    a = ap.parse_args()
    lig, BL, WI, EW, ER, n_teste = BA.charger_balayage(a.source)
    lig['variante'] = [AN.nom_variante(l) for l in lig.to_dict('records')]
    out = {}
    txt = []
    # 1. sensibilité du walk-forward
    rows = []
    for n_min in (25, 50, 80):
        for crit in ('z', 'borne'):
            o, ch = wf(BL, n_min, crit)
            rows.append(dict(n_min_train=n_min, critere=crit, **{k: float(v) for k, v in o.items()},
                             choix=' / '.join(lig.loc[k, 'variante'] for k in ch)))
    S1 = pd.DataFrame(rows); out['wf_sensibilite'] = S1
    txt.append('== 1. Walk-forward de la procédure (hors échantillon, 4 plis concaténés)\n' +
               S1.drop(columns='choix').to_string(float_format=lambda x: '%.3f' % x))
    # 2. toutes les éligibles de l'apprentissage
    rows = []
    for p in range(AN.K_PLIS):
        Str = AN.stats_blocs(BL, list(range(p, p + AN.RATIO)))
        Ste = AN.stats_blocs(BL, [p + AN.RATIO])
        el = AN.eligible(Str, AN.N_MIN_TRAIN)
        s = Ste[el]
        ok = s['n'] > 0
        rows.append(dict(pli=p, n_variantes=int(el.sum()), ecart_pts_median=float(s.loc[ok, 'ecart_pts'].median()),
                         part_ecart_pos=float((s.loc[ok, 'ecart_pts'] > 0).mean()),
                         r_median=float(s.loc[ok, 'r_moyen'].median()), part_r_pos=float((s.loc[ok, 'r_moyen'] > 0).mean()),
                         part_taux_60_75=float(((s.loc[ok, 'taux'] >= .6) & (s.loc[ok, 'taux'] <= .75)).mean())))
    S2 = pd.DataFrame(rows); out['eligibles_test'] = S2
    txt.append('== 2. Variantes éligibles à l\'apprentissage, jouées sur le bloc test\n' +
               S2.to_string(float_format=lambda x: '%.3f' % x))
    # 3. déclencheurs seuls, par bloc
    base = lig[(lig['filtres'] == '-')]
    rows = []
    for (dec, sens, ut), g in base.groupby(['decl', 'sens', 'ut']):
        idx = g.index.to_numpy()
        par_bloc = []
        for q in range(BA.NBLOCS):
            Sq = AN.stats_blocs(BL[idx], [q])
            ok = Sq['n'] > 0
            par_bloc.append(float(Sq.loc[ok, 'ecart_pts'].median()) if ok.any() else np.nan)
        rows.append(dict(decl=dec, sens=sens, ut=ut, n_median=float(g['n'].median()),
                         ecart_pts_median=float(g['ecart_pts'].median()), ecart_r_median=float(g['ecart_r'].median()),
                         blocs_pos=int(np.nansum(np.array(par_bloc) > 0)), blocs=int(np.isfinite(par_bloc).sum()),
                         **{'b%d' % q: v for q, v in enumerate(par_bloc)}))
    S3 = pd.DataFrame(rows).sort_values('ecart_pts_median', ascending=False); out['declencheurs_seuls'] = S3
    txt.append('== 3. Déclencheurs seuls (médiane sur les 56 géométries), écart de taux par bloc chronologique\n' +
               S3.to_string(index=False, float_format=lambda x: '%.2f' % x))
    # 4. hypothèse nuit (fixée à l'avance)
    jeux, T, prep, _ = BA.preparer(a.source)
    rows = []
    for ut in D.UTS:
        jis = [ji for ji, p in enumerate(prep) if p['ut'] == ut]
        for dec in B.DECLENCHEURS:
            for sens in B.SENS:
                for g in B.geometries():
                    acc = {True: [], False: []}
                    for ji in jis:
                        p = prep[ji]
                        s = BA.signaux(p, dec, sens, ())
                        tab = T[(ji, g)]
                        idx, d = TB.trades_table(tab, *s)
                        nuit = jeux[ji]['df']['min_paris'].to_numpy()[idx] < 480
                        for nn in (True, False):
                            m = nuit == nn
                            acc[nn].append(np.stack([tab['gagne'][d[m], idx[m]].astype(float), p['P'][g][0][d[m], idx[m]],
                                                     tab['r'][d[m], idx[m]], p['P'][g][1][d[m], idx[m]]], 1))
                    A = {nn: np.concatenate(v) for nn, v in acc.items()}
                    if min(len(A[True]), len(A[False])) < 10:
                        continue
                    rows.append(dict(ut=ut, decl=dec, sens=sens, geo=B.nom_geo(g), n_nuit=len(A[True]), n_jour=len(A[False]),
                                     ecart_nuit=100 * (A[True][:, 0] - A[True][:, 1]).mean(),
                                     ecart_jour=100 * (A[False][:, 0] - A[False][:, 1]).mean(),
                                     r_nuit=A[True][:, 2].mean(), r_jour=A[False][:, 2].mean()))
    S4 = pd.DataFrame(rows); out['nuit'] = S4
    d_e = S4['ecart_nuit'] - S4['ecart_jour']; d_r = S4['r_nuit'] - S4['r_jour']
    lignes = ['cas (déclencheur × sens × UT × géométrie, >= 10 trades de chaque côté) : %d' % len(S4),
              'écart de taux nuit - jour : médiane %+.1f pts ; nuit meilleure dans %.0f %% des cas' % (d_e.median(), 100 * (d_e > 0).mean()),
              'R nuit - jour : médiane %+.3f ; nuit meilleure dans %.0f %% des cas' % (d_r.median(), 100 * (d_r > 0).mean())]
    for ut, g in S4.groupby('ut'):
        de = g['ecart_nuit'] - g['ecart_jour']; dr = g['r_nuit'] - g['r_jour']
        lignes.append('  %dm : écart %+.1f pts (%.0f %% des cas), R %+.3f (%.0f %%)' % (
            ut, de.median(), 100 * (de > 0).mean(), dr.median(), 100 * (dr > 0).mean()))
    for dec, g in S4.groupby('decl'):
        de = g['ecart_nuit'] - g['ecart_jour']; dr = g['r_nuit'] - g['r_jour']
        lignes.append('  %s : écart %+.1f pts (%.0f %% des cas), R %+.3f (%.0f %%)' % (
            dec, de.median(), 100 * (de > 0).mean(), dr.median(), 100 * (dr > 0).mean()))
    txt.append('== 4. Hypothèse fixée à l\'avance : la nuit (0 h-8 h Paris) est meilleure\n' + '\n'.join(lignes))
    out['nuit_resume'] = lignes
    with open(os.path.join(TB.SORTIES, 'complements_%s.pkl' % a.source), 'wb') as fh:
        pickle.dump(out, fh)
    with open(os.path.join(TB.SORTIES, 'complements.txt'), 'w') as fh:
        fh.write('\n\n'.join(txt) + '\n')
    print('\n\n'.join(txt))


if __name__ == '__main__':
    main()
