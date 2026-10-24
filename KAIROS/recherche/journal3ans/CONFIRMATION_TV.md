# Confirmation au testeur TradingView des préréglages 45 et 46 (17/10/2026)

Exports de Jeremy (backtest profond, 15 min, 24/10/2023 → 16/10/2026, 2 micros ; ES1! en contrat standard),
dossier `~/Ephore/KAIROS-data/45*46/`. A1 = oct. 2023 → oct. 2024, A2 = → oct. 2025, A3 = → oct. 2026
(trades / % gagnants / PF).

| Symbole | Préréglage | Trades | Gagnants | PF | Net | Baisse max | A1 | A2 | A3 |
|---|---|---|---|---|---|---|---|---|---|
| MNQ1! | **45** | 656 | **75,5 %** | **4,51** | +78 439 $ | 1 162 $ | 228/77 %/5,73 | 231/77 %/4,43 | 197/73 %/3,95 |
| MNQ1! | 46 | 1 566 | 66,3 % | 2,34 | +120 285 $ | 2 584 $ | 544/67 %/2,52 | 530/66 %/2,24 | 492/65 %/2,30 |
| MES1! | 45 | 733 | 70,1 % | 3,11 | +35 790 $ | 1 222 $ | 258/70 %/3,98 | 244/69 %/2,68 | 231/71 %/3,07 |
| MES1! | 46 | 1 678 | 61,6 % | 1,92 | +50 415 $ | 1 957 $ | 581/59 %/1,86 | 542/61 %/1,63 | 555/65 %/2,27 |
| ES1! | 45 | 727 | 72,2 % | 3,54 | +387 982 $ | 12 065 $ | 258/73 %/4,45 | 252/70 %/2,97 | 217/73 %/3,61 |
| ES1! | 46 | 1 677 | 63,1 % | 2,13 | +581 382 $ | 21 765 $ | 574/61 %/2,07 | 551/63 %/1,82 | 552/66 %/2,51 |

Le journal prévoyait pour le 45 sur MNQ1! ~77 % / PF ~5,4 : le vrai testeur donne 75,5 % / 4,51, chaque année
au-dessus de 73 % / PF 3,9. La recette tient aussi sur MES et ES, où elle n'a PAS été cherchée (le journal est
MNQ seul) : c'est l'argument le plus fort contre le surapprentissage. Sorties du 45 MNQ : 331 à l'objectif,
221 au temps, 66 au stop, 38 en fin de séance ; gain moyen 204 $, perte moyenne 139 $.
Point à vérifier côté TradingView : case « Remplir les ordres sur l'OHLC standard » cochée (sinon exécution
aux prix Heiken Ashi, résultats faux) — le code la force (`fill_orders_on_standard_ohlc=true`).
