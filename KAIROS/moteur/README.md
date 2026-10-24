# Moteur de backtest commun (KAIROS)

Moteur UNIQUE utilisé par tous les agents de recherche. Vrais prix, signal à la clôture, entrée à
l'ouverture suivante, multi-UT sans regard vers le futur, coûts par instrument, sortie forcée à
l'heure propfirm. Conventions détaillées en tête de `moteur.py`.

```python
import sys; sys.path[:0] = ['KAIROS/moteur', 'KAIROS/dataset']
import moteur as M, registre as RG
from charger import charger
df15 = M.charger_recherche(charger('…/CME_MINI_MNQ1!, 15_xxxx.csv'))      # DÉVELOPPEMENT seulement (75 %)
g = dict(instrument='MNQ', stop={'mode': 'atr', 'k': 2.0}, objectif={'mode': 'R', 'k': 2.0},
         break_even={'R': 1.0, 'ticks': 1}, sortie_signal={'long': 'hei_flip_bas', 'short': 'hei_flip_haut'},
         heure_sortie='15:59', plages_interdites=[('00:00', '08:00')], max_trades_jour=3)
trades = M.backtest(df15, long='clx_buy', short=None, gestion=g)             # noms de colonnes ou tableaux
m = M.metriques(trades); print(M.resume(m))
ref = M.reference_hasard(df15, 200, g, graine=1, long='clx_buy')            # mêmes heures, même fréquence
p = M.p_hasard(ref, m['r_moyen'])
plis = M.walk_forward(df15, k=5, ratio=3)                                    # [(apprentissage, test), …]
# multi-UT : signal 15m, exécution 2m (coupure du cadre d'exécution imposée aux deux)
# t2 = M.backtest(df2, long=df15['clx_buy'], gestion=g, df_signal=df15)
RG.ajouter_test(dict(agent='retournement', famille='Climax', recette='clx_buy, 2 ATR, 2R, BE 1R',
                     marche='MNQ', ut_signal='15', ut_entree='15', echantillon='dev', n_variantes_testees=12,
                     p_ref_hasard=p, verdict='à confirmer', trades=trades))
```

## API (`moteur.py`)

| Fonction | Rôle |
|---|---|
| `backtest(df, long, short, gestion, df_signal=None)` | trades (DataFrame, colonnes `COLONNES_TRADES`) |
| `GESTION_DEFAUT` | toutes les options (entrée marché/limite, stop ATR/points/niveau+marge+repli+sauter, objectif R/points/niveau+ratio min, break-even, suiveur ATR, partiel, sortie sur signal, sortie après N barres, heure propfirm, plages interdites/autorisées, max trades/jour, coûts) |
| `metriques(trades)` / `resume(m)` | n, % gagnants, R moyen + IC95 bootstrap par jour, PF, net, DD max $, t, Sharpe journalier, meilleurs/pires, part des 10 meilleurs |
| `reference_hasard(df, n, gestion, graine, long=, short=)` + `p_hasard` | entrées au hasard (même heure Paris, même sens, mêmes barres autorisées), même gestion |
| `decoupage(df)` / `date_coupure(df)` | 75 % développement / 25 % scellé, coupé à une frontière de journée CME |
| `charger_recherche(source, ouvrir_scelle=False)` | ne renvoie que le développement ; `True` -> (dev, scellé) + trace dans `registre/ouvertures_scelle.log` |
| `walk_forward(df, k, ratio, ancre)` | k plis glissants (ou ancrés) par blocs de journées |
| `registre.ajouter_test(dict)` | ligne dans `registre/registre_tests.csv` (verrou fcntl, id `PRÉ-0001` par agent), trades dans `registre/trades/<id>.csv`, métriques remplies depuis `trades` |

Colonnes des trades : `entree_t, sortie_t` (Europe/Paris), `sens` (`long`/`short`), `prix_entree`
(glissement compris), `stop_initial, objectif` (NaN si aucun), `prix_sortie, motif_sortie` (`stop`,
`stop_be`, `stop_suiveur`, `objectif`, `signal`, `temps`, `heure`, `fin_donnees`, préfixe `partiel+`),
`r, pnl_usd` (1 contrat, net), `risque_usd` (1 R), `mae_usd` (<= 0) / `mfe_usd` (>= 0) latents,
`barres`, `niveau_stop` (`atr2`, `pts20`, `niveau:<nom>`, `repli_atr2`), `niveau_objectif`.
Compatible avec `propfirm/simulateur.py` (vérifié : `simule_chemin(trades, regles)` tourne).

## Conventions à connaître
- Données : index (ou colonne `time`) = OUVERTURE de la barre ; prix pris dans `o/h/l/c` (vrais prix du
  dataset), sinon `open/high/low/close` ; jamais `ha_*`. ATR = colonne `atr`, sinon ATR14 de Wilder.
- Tous les tableaux « signal » (entrées, sorties, niveaux, prix limites, ATR du stop) sont lus sur les
  barres signal à la clôture ; en multi-UT l'ordre part sur la 1re barre d'exécution qui ouvre après
  cette clôture (15m -> 2m : signal 10:00-10:15 -> entrée 10:16). Suiveur : ATR des barres d'exécution.
- Stop/objectif même barre -> stop. Écart à l'ouverture au-delà du stop -> sortie à l'ouverture.
  Ordres limites (objectif, partiel, entrée limite) : remplis si le prix dépasse le niveau d'1 tick,
  sans glissement (option `glissement_sur_limites`).
- Heure propfirm : à plat à la clôture de la dernière barre qui finit avant 15:59 Chicago (zoneinfo :
  22:59 Paris en général, 21:59 pendant les semaines de décalage été/hiver), aucune entrée ni position
  de 15:59 à 17:00 Chicago. Les demi-séances des jours fériés CME ne sont PAS gérées.
- Coûts par défaut : MNQ 2 $/pt, MES 5 $/pt (commission 0,62 $/côté), NQ 20 $/pt, ES 50 $/pt
  (2,25 $/côté), glissement 1 tick/côté (entrée marché, stop, sorties marché).
- Partiel : modèle fractionnaire (une fraction du contrat), utile pour plusieurs contrats.
- Multi-UT et scellé : les historiques 2m sont bien plus courts que les 15m ; en multi-UT, imposer aux
  deux cadres la coupure du cadre d'exécution (`decoupage(df15, coupure=M.date_coupure(df2))`).

## Validation
- `test_moteur.py` (23 tests, barres construites à la main) : SL+TP même barre, écart à travers le stop,
  break-even, suiveur, partiel, niveaux, entrée limite, heure propfirm hiver / semaine décalée / été,
  multi-UT 15m->5m/2m sans fuite du futur, registre en écriture concurrente (4 processus), découpage,
  référence au hasard, performance (40 000 barres ≈ 0,1 s).
- `verif_concordance.py` : préréglages A et C rejoués sur les 32 séries existantes (`tools/strategie/
  cache_series.pkl` + « Jeu 15:10 ») avec les conventions de `tools/strategie/engine.py` :
  **374 / 374 trades identiques** (barre d'entrée, sens, R et $ au 1e-9).
  Différences VOLONTAIRES des réglages par défaut par rapport à engine.py : commissions par instrument
  (engine.py : 1,25 $/côté partout, NQ à 20 $/pt), objectif rempli au prix (engine.py : objectif - 1 tick),
  arrondi des stops au tick, sortie forcée 15:59 Chicago (engine.py : 16:00 New York, option), trade
  ouvert en fin de données clôturé (`fin_donnees`) au lieu d'être abandonné.

```bash
~/venv-quant/bin/python KAIROS/moteur/test_moteur.py
~/venv-quant/bin/python KAIROS/moteur/verif_concordance.py
```
