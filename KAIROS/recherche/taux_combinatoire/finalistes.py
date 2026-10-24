"""Étape 5 : les 3 meilleures recettes du développement (une par famille), rejouées par le MOTEUR, placebo
`moteur.reference_hasard` (500 tirages par jeu), simulateur Tradeify Select Flex, ligne de préréglage Pine,
registre (--registre). Écrit sorties/finalistes.csv et sorties/finalistes.md.

    ~/venv-quant/bin/python finalistes.py [--source cache|dataset] [--registre]
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import analyse as AN  # noqa: E402
import balayage as BA  # noqa: E402
import bib_wrx as B  # noqa: E402
import donnees_wrx as D  # noqa: E402
import tables as TB  # noqa: E402

M = D.M
sys.path.insert(0, os.path.join(D.SB, 'propfirm'))
sys.path.insert(0, os.path.join(D.SB, 'moteur'))
import simulateur as SIM  # noqa: E402
import registre as RG  # noqa: E402

N_PLACEBO = 500
N_REF_PROPFIRM = 100
TAILLES = list(range(1, 11))


def choisir(lig, k=3):
    """Éligibles du développement triées par z d'écart de taux ; on saute une recette du même déclencheur qui
    partage au moins 2 filtres avec une recette déjà prise (sinon on aurait 3 fois la même)."""
    C = lig[lig['eligible_dev']].sort_values('z_ecart', ascending=False)
    pris = []
    for i, l in C.iterrows():
        fs = set(l['filtres'].split('+')) - {'-'}
        if any(l['decl'] == p['decl'] and len(fs & (set(p['filtres'].split('+')) - {'-'})) >= 2 for p in pris):
            continue
        if any(l['decl'] == p['decl'] and l['filtres'] == p['filtres'] for p in pris):
            continue
        pris.append(l)
        if len(pris) >= k:
            break
    return pris


def ligne_pine(l, contrats):
    dec = l['decl']
    on = set(B.TOUS) if dec == 'tous' else {dec}
    e = ['sens=%s' % {'long': 'Long seulement', 'short': 'Short seulement', 'les_deux': 'Les deux'}[l['sens']],
         'clx=%d' % ('clx' in on), 'sig=%d' % ('sig_fort' in on)]
    if 'sig_fort' in on:
        e.append('sigNiv=Fort seulement')
    e += ['hei=%d' % ('hei_flip' in on), 'tl=%d' % ('tl' in on), 'lvl=%d' % ('lvl' in on)]
    fs = [] if l['filtres'] == '-' else l['filtres'].split('+')
    g = {B.FILTRE_GROUPE[f]: f for f in fs}
    f_txt = ['feu=0', 'tr=0', 'ema=0', 'adx=0', 'det=0', 'clxF=0', 'bo=0', 'hr=0']
    cle = {'feu': 0, 'tr': 1, 'ema': 2, 'adx': 3, 'det': 4, 'clx': 5, 'bo': 6, 'hr': 7}
    for grp, f in g.items():
        f_txt[cle[grp]] = B.FILTRE_PINE[f]
    t = ';'.join(e + f_txt + ['maxJour=0', 'taille=Contrats fixes', B.geo_pine((l['stop'], l['obj'], l['extra']))])
    manque = []
    if l['extra'] == 'temps':
        manque.append('SORTIE TEMPORELLE absente du Pine : il faut une option « sortir à l\'ouverture de la bougie '
                      'qui suit N bougies de position » (N = %d en %d min, soit %d min ; moteur : sortie_barres, '
                      'sortie au marché à l\'ouverture suivante, priorité heure propfirm > signal > temps).'
                      % (max(1, B.TEMPS_MIN // int(l['ut'])), l['ut'], B.TEMPS_MIN))
    if 'tr240' in fs:
        manque.append('régler à la main « TREND : unité » = 240 (non pilotable par préréglage).')
    if 'tr60' in fs:
        manque.append('« TREND : unité » = 60 (valeur par défaut).')
    if 'lvl' in on:
        manque.append('régler à la main « Niveaux mesurés sur » = Vrais prix (le balayage mesure les sessions et le '
                      'Monday sur les vrais prix).')
    if any(f.startswith('feu') for f in fs):
        manque.append('Feu : le cache n\'a qu\'un SUBSTITUT de Feu (8 à 16 voix) ; le seuil Pine porte sur 29 voix.')
    manque.append('nombre de contrats : %d micro(s) dans « Contrats fixes » (non pilotable par préréglage).' % contrats)
    return t, manque


def trades_moteur(jeux, l):
    g = (l['stop'], l['obj'], l['extra'])
    out, sig = [], []
    for ji, j in enumerate(jeux):
        if j['ut'] != l['ut']:
            continue
        p = dict(dec={k: B.declencheur(j['df'], k) for k in B.DECLENCHEURS}, filtres=B.masques_filtres(j['df']))
        fs = () if l['filtres'] == '-' else tuple(l['filtres'].split('+'))
        s = BA.signaux(p, l['decl'], l['sens'], fs)
        G = B.gestion(j['df'], j['instrument'], g, j['ut'])
        T = M.backtest(j['df'], long=s[0], short=s[1], gestion=G)
        T['jeu'] = j['nom']
        out.append(T); sig.append((ji, s, G))
    return pd.concat(out, ignore_index=True).sort_values('entree_t').reset_index(drop=True), sig


def placebo(jeux, sig, graine=11):
    """reference_hasard du moteur, N_PLACEBO tirages par jeu, regroupés tirage par tirage."""
    par_tirage = [[] for _ in range(N_PLACEBO)]
    for ji, s, G in sig:
        R, trs = M.reference_hasard(jeux[ji]['df'], N_PLACEBO, G, graine=graine + ji, long=s[0], short=s[1],
                                    garder_trades=True)
        for k, T in enumerate(trs):
            if len(T):
                par_tirage[k].append(T)
    tir = [pd.concat(t, ignore_index=True).sort_values('entree_t').reset_index(drop=True) for t in par_tirage if t]
    taux = np.array([(t['pnl_usd'] > 0).mean() for t in tir]); r = np.array([t['r'].mean() for t in tir])
    return tir, taux, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=D.SOURCE)
    ap.add_argument('--registre', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    lig = pd.read_csv(os.path.join(TB.SORTIES, 'balayage_complet.csv.gz'))
    with open(os.path.join(TB.SORTIES, 'analyse_%s.pkl' % a.source), 'rb') as fh:
        AZ = pickle.load(fh)
    lig_bl, BL, *_ = BA.charger_balayage(a.source)
    jeux = D.charger_jeux(a.source)
    flex = SIM.charge_regles()['tradeify_50k_select_flex']
    res, md = [], []
    for rang, l in enumerate(choisir(lig), 1):
        T, sig = trades_moteur(jeux, l)
        m = M.metriques(T)
        assert m['n'] == l['n'] and abs(m['r_moyen'] - l['r_moyen']) < 1e-3, ('moteur et table divergent', m['n'], l['n'], m['r_moyen'], l['r_moyen'])
        tir, ptaux, pr = placebo(jeux, sig)
        taux = m['pct_gagnants']
        p_taux = float((1 + (ptaux >= taux).sum()) / (1 + len(ptaux)))
        p_r = float((1 + (pr >= m['r_moyen']).sum()) / (1 + len(pr)))
        tab, best = SIM.optimise_taille(T, flex, tailles=TAILLES, critere='valeur_esperee', n_sim=1000, ordre='prudent')
        c = int(best.get('contrats', 1))
        ref = SIM.analyse_reference(tir[:N_REF_PROPFIRM], flex, c, n_sim=4000, ordre='prudent')
        # blocs chronologiques (dans l'échantillon : la recette a été choisie sur tout le développement)
        k = int(l.name)
        bl = []
        for q in range(BA.NBLOCS):
            Sq = AN.stats_blocs(BL[k:k + 1], [q]).iloc[0]
            bl.append('%d tr. %.0f %% / %.0f %%' % (Sq['n'], 100 * Sq['taux'], 100 * Sq['taux_placebo']) if Sq['n'] else '—')
        pine, manque = ligne_pine(l, c)
        r = dict(rang=rang, variante=l['variante'], ut=l['ut'], n=m['n'], taux=taux, taux_placebo_moteur=float(ptaux.mean()),
                 ecart_pts=100 * (taux - ptaux.mean()), p_taux=p_taux, r_moyen=m['r_moyen'], r_placebo=float(pr.mean()),
                 p_r=p_r, ic95_r=m['r_ic95'], pf=m['pf'], net_usd=m['gain_net_usd'], dd_usd=m['dd_max_usd'],
                 p_white_taux=l['p_white_taux'], p_white_r=l['p_white_r'], blocs_ecart_pos=l['blocs_ecart_pos'],
                 contrats=c, p_flex=best.get('p_reussite'), p1_payout=best.get('p_1er_payout'),
                 ve_usd=best.get('valeur_esperee_usd'), p_flex_hasard=ref.get('p_reussite'),
                 p1_hasard=ref.get('p_1er_payout'), ve_hasard=ref.get('valeur_esperee_usd'), pine=pine,
                 manque=' | '.join(manque), blocs=' ; '.join(bl), taux_mes=l['taux_mes'], taux_nq=l['taux_nq'],
                 r_mes=l['r_mes'], r_nq=l['r_nq'])
        res.append(r)
        print('%d. %s\n   n=%d taux %.1f %% placebo %.1f %% (p=%.3f) R %+.3f (placebo %+.3f, p=%.3f) PF %.2f | White p %.2f/%.2f'
              ' | Tradeify %d micros P=%.2f (hasard %.2f) VE %+.0f (hasard %+.0f)' % (
                  rang, r['variante'], r['n'], 100 * taux, 100 * ptaux.mean(), p_taux, r['r_moyen'], r['r_placebo'], p_r,
                  r['pf'], r['p_white_taux'], r['p_white_r'], c, r['p_flex'], r['p_flex_hasard'], r['ve_usd'],
                  r['ve_hasard']), flush=True)
        if a.registre:
            o = AZ['oos1']
            verdict = ('REJETÉ : critère 1 non tenu (walk-forward de la procédure : %.0f %% gagnants contre %.0f %% au '
                       'placebo, R %+.2f, n=%d) ; White p=%.2f ; dev : %.0f %% vs placebo %.0f %% (p=%.3f), R %+.2f'
                       % (100 * o['taux'], 100 * o['taux_placebo'], o['r_moyen'], o['n'], l['p_white_taux'],
                          100 * taux, 100 * ptaux.mean(), p_taux, m['r_moyen']))
            Tr = T.drop(columns=['jeu'])
            idr = RG.ajouter_test(dict(agent='WRX', famille='taux_combinatoire/' + l['decl'], recette=l['variante'],
                                       marche='MES+MNQ (micros)', ut_signal=str(l['ut']), ut_entree=str(l['ut']),
                                       echantillon='dev_%s' % a.source, n_variantes_testees=int(AZ['n_teste']),
                                       p_tradeify=r['p_flex'], p_ref_hasard=r['p_flex_hasard'], verdict=verdict,
                                       trades=Tr), prefixe='WRX')
            r['registre'] = idr
            print('   registre :', idr)
    F = pd.DataFrame(res)
    F.to_csv(os.path.join(TB.SORTIES, 'finalistes.csv'), index=False, float_format='%.4f')
    print('finalistes : %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
