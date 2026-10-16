"""EXH — génère RESULTATS.md depuis balayage_complet.csv, meta_balayage.json, wf_procedure.csv, finalistes.csv."""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))


def f(x, d=2, signe=True):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return '—'
    return ('%+.*f' if signe else '%.*f') % (d, x)


def main():
    t = pd.read_csv(os.path.join(ICI, 'balayage_complet.csv'))
    meta = json.load(open(os.path.join(ICI, 'meta_balayage.json')))
    wf = pd.read_csv(os.path.join(ICI, 'wf_procedure.csv'))
    fin = pd.read_csv(os.path.join(ICI, 'finalistes.csv')) if os.path.exists(os.path.join(ICI, 'finalistes.csv')) else None
    N_MIN = 20
    ok = t[(t.n >= N_MIN) & (t.doublon_de < 0)].sort_values('note', ascending=False)
    L = []
    w = L.append
    w('# Explorateur exhaustif (EXH) — résultats\n')
    w('Données : `%s` (séries Python ≈ 2 mois, vrais prix reconstitués), **développement seulement** (75 %%, '
      'scellé non ouvert). MES et NQ regroupés par unité, tradés en micros (MES / MNQ), coûts du moteur, '
      'intrajournée forcée (15:59 Chicago). Relancer sur le DATASET : `balayage.py --source dataset` puis '
      '`finalistes.py --registre` puis `rapport.py`.\n' % meta.get('source'))
    w('## Verdict\n')
    w('- **%d variantes testées** (%d classables : ≥ %d trades, sans doublon).' % (meta['n_variantes'], len(ok), N_MIN))
    w('- **Reality Check de White sur toutes les variantes classables : p = %.2f** (meilleure : `%s`). '
      '%s' % (meta['p_white'], meta['meilleur_white'],
              'Le meilleur résultat du balayage est compatible avec le hasard (biais de sélection).' if meta['p_white'] > 0.05
              else 'Le meilleur résultat bat le hasard au seuil 5 % — à confirmer sur le DATASET.'))
    w('- **Walk-forward de la procédure** (choisir le n°1 du classement sur 2 blocs, le jouer sur le bloc suivant, '
      '4 plis) : R moyen hors échantillon du n°1 = %s ; des 10 premiers = %s ; de toutes les variantes = %s.' % (
          f(wf['r_test_n1'].mean()), f(wf['r_test_top10'].mean()), f(wf['r_test_tous'].mean())))
    dsr = meta.get('dsr', {})
    if dsr:
        vals = [v[0] for v in dsr.values() if v and v[0] == v[0]]
        w('- **Deflated Sharpe** (N = %d essais) des 20 premiers : max %.2f (il faudrait > 0,95).' % (
            meta['n_variantes'], max(vals) if vals else float('nan')))
    if fin is not None and len(fin):
        b = fin.sort_values('note', ascending=False).iloc[0]
        w('- Monte-Carlo Tradeify Select Flex sur les %d finalistes : P(réussite) de %.0f %% à %.0f %%, contre '
          '%.0f %% à %.0f %% pour les entrées au hasard avec la même gestion.' % (
              len(fin), 100 * fin.p_flex.min(), 100 * fin.p_flex.max(), 100 * fin.p_ref_flex.min(), 100 * fin.p_ref_flex.max()))
    w('- **Conclusion : rien de robuste sur ces données** (aucune recette ≥ 200 trades ; IC95 larges ; '
      'sélection non distinguable du hasard). La machine est prête : même code sur le DATASET.\n')

    w('## Méthode\n')
    w('1. Étape 1 : chaque déclencheur seul × mode (suivi / inverse = jouer contre l\'événement) × sens (long, short, '
      'les deux) × unité (5, 15, 30, 60 min), gestion de référence stop 2 ATR / objectif 2R.')
    w('2. Étape 2 : les 30 meilleures bases (≤ 3 par déclencheur) + chacun des filtres disponibles.')
    w('3. Étape 3 : paires parmi les 8 meilleurs filtres de chaque base (20 bases), puis 3e filtre sur les 10 meilleures.')
    w('4. Étape 4 : 12 finalistes × 6 stops (1-4 ATR, niveau de protection) × 7 objectifs (1-4R, aucun, prochain '
      'niveau) × 5 options (rien, break-even 1R, suiveur 3 ATR, sortie Heishinator, sortie après 16 barres).')
    w('5. Note robuste = borne basse de l\'IC80 du R moyen (bootstrap par journée CME), −1 si < 20 trades, −0,5 si '
      '< 12 journées (le 5 min n\'en a que ~6 : non classable), −0,25 si moins de la moitié des blocs '
      'chronologiques (4 par jeu) sont positifs, −0,1 si un des deux marchés est négatif.')
    w('6. Biais de sélection : Reality Check de White (bootstrap stationnaire, blocs de 5 jours) sur le R journalier '
      'de toutes les variantes classables ; Deflated Sharpe ; walk-forward de la procédure de sélection.')
    w('7. Finalistes : `simulateur.optimise_taille` (Select Flex, ordre prudent, 1 000 parcours) et référence '
      '`reference_hasard` (20 tirages, même gestion, même heure) passée au même simulateur.\n')

    w('## Top 20 (note robuste, toutes étapes, sans doublon)\n')
    w('| # | recette (déclencheur·mode·sens·UT·filtres·sortie) | n | R moyen | IC95 | PF | blocs + | R MES | R NQ | note |')
    w('|---|---|---|---|---|---|---|---|---|---|')
    for k, (_, r) in enumerate(ok.head(20).iterrows(), 1):
        w('| %d | `%s` | %d | %s | [%s ; %s] | %.2f | %.0f %% | %s | %s | %s |' % (
            k, r.recette, r.n, f(r.r_moyen), f(r.ic95_bas), f(r.ic95_haut), r.pf, 100 * (r.frac_blocs_pos if r.frac_blocs_pos == r.frac_blocs_pos else 0),
            f(r.r_MES), f(r.r_NQ), f(r.note)))
    w('')
    if fin is not None and len(fin):
        w('## Finalistes : Monte-Carlo Tradeify\n')
        w('| recette | n | R moyen | taille (micros) | P(réussite) Flex | P hasard | P(1er payout) | VE $ | P Growth | p hasard (R) |')
        w('|---|---|---|---|---|---|---|---|---|---|')
        for _, r in fin.sort_values('note', ascending=False).iterrows():
            w('| `%s` | %d | %s | %d | %.0f %% | %.0f %% | %.0f %% | %+.0f | %.0f %% | %.2f |' % (
                r.recette, r.n, f(r.r_moyen), r.contrats, 100 * r.p_flex, 100 * r.p_ref_flex, 100 * r.p1_payout,
                r.ve_usd, 100 * r.p_growth, r.p_hasard_r))
        w('')
        w('Lecture : le Monte-Carlo ré-échantillonne par blocs de journées les ~30 trades de ~3 semaines : une '
          'P(réussite) proche de 100 % veut seulement dire « si l\'avenir ressemblait exactement à ces 3 semaines ». '
          'La référence au hasard (même gestion, mêmes heures) est elle aussi très haute sur cette période haussière : '
          'c\'est l\'écart à la référence qui compte, et il n\'est pas confirmé par le walk-forward.\n')
    w('## Walk-forward de la procédure de sélection\n')
    w('Approximation : les variantes des étapes 2-4 ont été construites en regardant tout le développement ; le '
      'walk-forward refait seulement le CHOIX final (il est donc plutôt optimiste).\n')
    w('| pli | candidats | n°1 choisi sur l\'apprentissage | note app. | R test n°1 (n) | R test top 10 | R test tous |')
    w('|---|---|---|---|---|---|---|')
    for _, r in wf.iterrows():
        w('| %d | %d | `%s` | %s | %s (%d) | %s | %s |' % (r.pli, r.n_candidats, r.choisi, f(r.note_app), f(r.r_test_n1),
                                                     r.n_test_n1, f(r.r_test_top10), f(r.r_test_tous)))
    w('')

    # carte de ce qui ne marche jamais
    w('## Carte : ce qui ne marche jamais\n')
    e = ok.groupby('evenement').agg(variantes=('n', 'size'), part_r_pos=('r_moyen', lambda x: (x > 0).mean()),
                                    meilleur_r=('r_moyen', 'max'), meilleure_note=('note', 'max'),
                                    r_median=('r_moyen', 'median')).sort_values('meilleure_note')
    s1e = t[(t.etape == 1) & (t.n >= 10)].groupby('evenement').agg(c1=('n', 'size'), p1=('r_moyen', lambda x: (x > 0).mean()),
                                                                   m1=('r_moyen', 'median'))
    e = e.join(s1e, how='outer').fillna({'variantes': 0})
    jamais = e[(e.meilleure_note < 0)]
    w('**Déclencheurs dont AUCUNE variante classable n\'a une note positive** (borne basse IC80 < 0 partout, '
      'toutes UT, modes, sens, filtres, sorties) : %s.\n' % (', '.join('`%s`' % k for k in jamais.index) or 'aucun'))
    w('Lecture : « suivi » et « inverse » sont presque des images miroir avant coûts ; un déclencheur sans aucune '
      'note positive n\'a donc d\'avantage dans AUCUN des deux sens une fois les coûts payés.\n')
    w('Attention : les déclencheurs promus aux étapes 2-4 ont beaucoup plus de variantes (et donc plus de chances '
      'd\'avoir un « gagnant » par hasard). La colonne « étape 1 » compare à armes égales (déclencheur seul, '
      '12 à 24 combinaisons UT × mode × sens, ≥ 10 trades).\n')
    w('| déclencheur | étape 1 : combinaisons | étape 1 : part R > 0 | étape 1 : R médian | variantes classables (toutes étapes) | meilleur R | meilleure note |')
    w('|---|---|---|---|---|---|---|')
    for k, r in e.sort_values('m1').iterrows():
        w('| %s | %s | %s | %s | %d | %s | %s |' % (k, '%d' % r.c1 if r.c1 == r.c1 else '—',
                                                 '%.0f %%' % (100 * r.p1) if r.p1 == r.p1 else '—', f(r.m1),
                                                 r.variantes, f(r.meilleur_r), f(r.meilleure_note)))
    w('')
    s1 = t[(t.etape == 1) & (t.n >= N_MIN)]
    m = s1.groupby('mode').r_moyen.median(); sn = s1.groupby('sens').r_moyen.median(); u = s1.groupby('ut').r_moyen.median()
    w('Étape 1 (déclencheur seul) — R médian : suivi %s / inverse %s ; long %s / short %s / les deux %s ; '
      'par UT : %s.\n' % (f(m.get('suivi')), f(m.get('inverse')), f(sn.get('long')), f(sn.get('short')),
                          f(sn.get('les_deux')), ', '.join('%dm %s' % (k, f(v)) for k, v in u.items())))
    # effet des filtres (étape 2 vs leur base)
    s2 = t[t.etape == 2].copy()
    if len(s2):
        base = t[t.etape == 1].set_index(['evenement', 'mode', 'sens', 'ut'])['r_moyen']
        s2['r_base'] = [base.get((a, b, c, d), np.nan) for a, b, c, d in zip(s2.evenement, s2['mode'], s2.sens, s2.ut)]
        s2['delta'] = s2.r_moyen - s2.r_base
        g = s2[s2.n >= 10].groupby('filtres').agg(bases=('delta', 'size'), delta_moyen=('delta', 'mean'),
                                                   part_amelioree=('delta', lambda x: (x > 0).mean())).sort_values('delta_moyen')
        w('**Effet moyen de chaque filtre** (étape 2, Δ R moyen par rapport à la base sans filtre, bases avec ≥ 10 trades). '
          'Les filtres en tête de liste dégradent presque toujours :\n')
        w('| filtre | bases | Δ R moyen | part des bases améliorées |')
        w('|---|---|---|---|')
        for k, r in g.iterrows():
            w('| %s | %d | %s | %.0f %% |' % (k, r.bases, f(r.delta_moyen), 100 * r.part_amelioree))
        w('')
    s4 = t[t.etape == 4]
    if len(s4):
        w('**Sorties (étape 4, R moyen médian sur les finalistes)** — stop : %s ; objectif : %s ; option : %s.\n' % (
            ', '.join('%s %s' % (k, f(v)) for k, v in s4.groupby('stop').r_moyen.median().items()),
            ', '.join('%s %s' % (k, f(v)) for k, v in s4.groupby('objectif').r_moyen.median().items()),
            ', '.join('%s %s' % (k, f(v)) for k, v in s4.groupby('extra').r_moyen.median().items())))
    w('## Limites\n')
    w('- ≈ 3 semaines de développement par jeu en 15/30 min (7 semaines pour MES1 avril-juin, 6 semaines en 60 min), '
      '~6 jours en 5 min : toutes les recettes ont < 200 trades, aucune ne peut être « probante » au sens de SPEC.md.')
    w('- Régime : surtout haussier (sept.-oct.) ; MES1 n\'a ni volume (pas de climax ni Detector) ni flèches '
      'recalculées (flèches de l\'original).')
    w('- Feu = **substitut** (vote par le sens de 8 à 16 états disponibles) tant que le DATASET n\'est pas là ; '
      'blocs SuperTrader/SIGNAL (VIDYA, MACD 10 min, PA, LinReg, ORB du SIGNAL) et divergences RSI absents du cache : '
      'leurs filtres/déclencheurs s\'activent tout seuls avec le DATASET.')
    w('- Niveaux de session / ORB / Monday / veille recalculés sur vrais prix (dernière fenêtre terminée) ; '
      'ORB non défini au-dessus de 30 min.')
    w('- MES et NQ sur des périodes en partie communes : trades corrélés, l\'IC par journée en tient compte en partie.')
    w('\n## Fichiers\n')
    w('`donnees_exh.py` (accès données, une seule fonction `charger_jeux`), `bibliotheque.py` (déclencheurs, filtres, '
      'sorties), `balayage.py` (étapes 1-4, notation, White, DSR, walk-forward), `finalistes.py` (Monte-Carlo, '
      'registre), `rapport.py` ; sorties : `balayage_complet.csv`, `wf_procedure.csv`, `finalistes.csv`, '
      '`meta_balayage.json`, `journal_balayage.txt`.')
    open(os.path.join(ICI, 'RESULTATS.md'), 'w').write('\n'.join(L) + '\n')
    print('RESULTATS.md écrit')


if __name__ == '__main__':
    main()
