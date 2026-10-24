# Journal 3 ans (JR3) — MNQ1! 15 min, 24/10/2023 → 16/10/2026, 5 658 trades (préréglage 99), 2 micros

Code : `charge.py` (parse), `feat.py` (variables dans le sens du trade), `filtres.py` (rejeu 40 / 44), `moteur.py` (recherche en faisceau), `perm.py` (permutation), `q*.py` (étapes), `regles_figees.py`, `reg.py` (registre JR3-0001 à 0003).
Heures = heure de Paris. « dans le sens » : long = bougie HA haussière / valeur telle quelle ; short = l'inverse (écart e multiplié par -1).

## 1. Le journal reproduit-il le vrai 40 / 44 ?

Filtre rejoué sur le journal : biais F ≥ 5 et I ≥ 3 (long), F ≤ -5 et I ≤ -3 (short), au moins un déclencheur parmi F M H T N C (pas D seul), place Detector z ≥ 1,5.

| | Trades | % gagnants | PF | Net 2 micros $ |
|---|---|---|---|---|
| Vrai export 40 (4 micros, net ÷ 2) | 1 228 | 55,3 | 1,26 | 27 244 |
| Journal, filtre 40 | 1 020 | 54,2 | 1,21 | 18 591 |
| Vrai 44 (= 40 sans 8 h-10 h) | 1 049 | 57,0 | 1,35 | 31 364 |
| Journal, filtre 44 | 869 | 56,3 | 1,31 | 23 336 |

Écart : le journal a 17 % de trades en moins (le vrai run en a ~1,2 fois plus), -0,7 point de % gagnants et -0,04 de PF. 950 des 1 228 trades du vrai 40 sont aussi dans le journal et leur issue est identique à 100 % (raison de sortie et P&L). Les 278 absents du journal (un trade du journal était ouvert) ont PF 1,27 ; les 70 en trop ont PF 0,64. Conclusion : le journal est fidèle trade par trade et légèrement pessimiste en volume. Un filtre rejoué sur lui donne un résultat un peu bas, pas un résultat gonflé. Note : aucun export 44 en 2 micros n'existe ; le « vrai 44 » est le 40 sans entrées 8 h-9 h 59 (net ÷ 2). L'énoncé donne 1 067 trades / +31 808 $ / DD 6 840 $ pour le vrai 44 ; ma reconstruction donne 1 049 / +31 364 $ / DD 6 664 $.

## 2. Méthode (développement = 24/10/2023 → 23/10/2025 ; test = 24/10/2025 → 16/10/2026)

Recherche en faisceau (largeur 300) de conjonctions de 1 à 4 conditions sur 41 variables (F, I, Feu, TREND et Dashator par unité, STRENGTH, ADX, DI, z, e, v, climax, déclencheurs, sens, heure, jour), 285 seuils aux déciles, score = borne basse de Wilson du % gagnants avec n ≥ 340 en développement (≈ 500 sur 3 ans) et PF ≥ 1. 172 086 conjonctions évaluées. Arbre de profondeur ≤ 3 : il retrouve les mêmes variables (Dashator 240 et e).
Contrôle du surapprentissage : permutation des résultats entre trades, 500 fois, même recherche complète. Le meilleur score du hasard atteint au plus 63,8 % de gagnants ; la vraie règle fait 77,7 % : p = 0,002. Le seuil de e est en plateau : 78,8 % (≤ 0,3), 77,3 % (≤ 0,6), 72,6 % (≤ 0,9), 69,0 % (≤ 1,2), 65,9 % (≤ 1,5) ; chaque condition retire des trades et monte le %, sans falaise avant 0,6-0,9.

Ce qui compte : (1) Dashator 240 min dans le sens, (2) Dashator 60 min dans le sens, (3) e = (clôture HA - EMA50) / ATR dans le sens du trade ≤ 0,6, donc le prix n'est pas déjà étiré. Les autres conditions du top 10 (Feu, I, F, z) n'ajoutent rien : elles reviennent au même sous-ensemble. Effet marginal, développement → test :

| Règle | Dév. n / % / PF | Test n / % / PF |
|---|---|---|
| Dashator 240 seul | 2 361 / 55,6 / 1,30 | 1 044 / 58,0 / 1,43 |
| + Dashator 60 | 2 269 / 56,3 / 1,34 | 1 017 / 58,0 / 1,44 |
| Dashator 240 + e ≤ 0,6 (2 conditions) | 395 / 73,9 / 3,98 | 157 / 75,2 / 4,39 |
| **R* = Dash 60 + Dash 240 + e ≤ 0,6** | 348 / 77,3 / 5,30 | 143 / 76,9 / 5,47 |

## 3. Gestion (bornes, objectif 0,75 R)

Objectif 0,75 R, stop 1 R, MFE/MAE en R, ordre inconnu quand les deux sont touchés (2 trades sur 348). R* : % gagnants 77,3 → 79,3 / 79,9, mais PF 5,3 → 4,7 / 4,9 et net 38 133 → 31 024 / 31 641 $ (bornes prudente / optimiste). Pas net dans les deux bornes (le % monte, PF et net baissent) : **on garde 1 R**. Un objectif 1,25 R n'est pas estimable : le journal sort à 1 R, la MFE ne dit rien au-delà ; il ferait baisser le % gagnants de toute façon.

## 4. Évaluation sur l'année de test (règles figées avant ouverture du test, regardée une seule fois)

| Période | Règle | Trades | % gagnants | PF | Net $ | Baisse max $ |
|---|---|---|---|---|---|---|
| Dév. | R* (journal) | 348 | 77,3 | 5,30 | 38 133 | 829 |
| Dév. | filtre 44 (journal) | 579 | 56,0 | 1,30 | 12 737 | 3 155 |
| Dév. | vrai 44 | 699 | 55,9 | 1,25 | 12 915 | 5 397 |
| **Test** | **R* (journal)** | **143** | **76,9** | **5,47** | **23 071** | **573** |
| Test | Alternative (e ≤ 1,5) | 419 | 66,1 | 2,39 | 43 881 | 2 990 |
| Test | filtre 44 (journal) | 290 | 56,9 | 1,33 | 10 599 | 5 533 |
| Test | vrai 40 | 403 | 56,8 | 1,38 | 16 452 | 7 693 |
| Test | vrai 44 | 350 | 59,1 | 1,50 | 18 449 | 6 664 |

Par année (R*) : 2023-24 179 trades, 74,9 %, PF 4,85, +17 124 $ ; 2024-25 169, 79,9 %, PF 5,74, +21 009 $ ; 2025-26 (test) 143, 76,9 %, PF 5,47, +23 071 $. Par trimestre : % gagnants entre 59 % et 92 % (hors le trimestre incomplet 2026T4, 7 trades), les 12 trimestres complets sont positifs. Test, intervalle à 95 % (rééchantillonnage) : % gagnants 69,9 à 83,9 ; PF 3,4 à 9,9. Longs 76,0 % / courts 77,9 % : pas de dépendance au sens. Seuls 10 % des trades de R* sont aussi dans le filtre 44 : c'est une autre population, pas un 44 amélioré.
Profil de R* : risque moyen 261 $ par trade (65 points, jusqu'à 1 213 $), pire perte 524 $, 3 trades par semaine, 168 sorties au temps sur 491. Attendu en vrai run : ~590 trades (491 × 1,2), donc juste au-dessus des 500 ; le seuil de 500 n'est pas garanti.

Simulateur Tradeify Select Flex (2 micros, trades du journal) :

| Trades | Période | P(réussite) bootstrap / chrono | P(1er payout) | Valeur espérée $ (boot. / chrono) |
|---|---|---|---|---|
| R* | test | 100 % / 86,4 % | 100 % / 73,6 % | 6 147 / 4 069 |
| R* | 3 ans | 100 % / 95,6 % | 100 % / 91,5 % | 6 324 / 5 627 |
| Alternative | test | 96,2 % / 86,6 % | 94,3 % / 76,4 % | 5 624 / 3 499 |
| filtre 44 (journal) | test | 56,8 % / 64,1 % | 44,8 % / 62,5 % | 1 192 / 1 639 |
| vrai 44 | test | 64,8 % / 66,4 % | 53,0 % / 64,1 % | 1 873 / 2 356 |

(Le chrono du test est pénalisé : les fenêtres de départ tardives sont censurées.)

## 5. Recommandation (UNE) : R*

Clés `f_pr_def` (base = préréglage 99 sans `jr`, mêmes entrées et même gestion, donc le sous-ensemble du journal est rejoué à l'identique) :

```
bias=0;sens=Les deux;sig=1;sigNiv=Fort + Moyen;hei=1;tl=1;lvl=1;clx=1;div=1;divX=2.5;tr=0;tr4h=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=0;maxJour=0;hr=0;be=0;trail=Aucun;oppArr=0;oppHei=0;fin=0;pf=1;part=0;tBar=8;stop=ATR × k;atrK=2;tp=En R;tpR=1;taille=Contrats fixes;fixe=2;dsh60=1;dsh240=1;eOn=1;eMax=0.6
```

Clés à AJOUTER dans la stratégie (4 nouvelles, toutes des interrupteurs ou seuils neutres si absentes) :

| Clé | Valeur | Sens exact |
|---|---|---|
| `dsh60` ⓘ | 1 (absent = 0 = coupé) | n'autoriser un long que si le Dashator 60 min (`t3_d4`, unité 4 par défaut = "60", déjà décalé d'une bougie clôturée par `f_mu_off`) est haussier ; un short que s'il est baissier |
| `dsh240` ⓘ | 1 (absent = 0) | idem avec le Dashator 240 min (`t3_d5`) |
| `eOn` ⓘ | 1 (absent = 0) | active le filtre d'écart |
| `eMax` | 0.6 (ATR) | long : `round((close - ema_m1) / sg_atr, 1) <= eMax` ; short : `round((close - ema_m1) / sg_atr, 1) >= -eMax`. Même formule que le champ `e` du journal (arrondi à 0,1 avant la comparaison pour retrouver exactement le journal) |

Aucune autre condition nouvelle. Pas de seuil en voix F/I, pas de Detector, pas de filtre d'heure, pas de sous-ensemble de déclencheurs.

## 6. Alternative au profil différent : « volume »

Même clés, avec `eMax=1.5` : journal 1 337 trades, 66,0 %, PF 2,31, net 102 108 $ en 3 ans (test : 419 / 66,1 % / 2,39 / +43 881 $, DD 2 990 $). Moins de gagnants (-11 points), PF 2 fois plus bas, mais 2,7 fois plus de trades et 1,9 fois plus de net ; plus sûr pour la limite de 500 trades. Le choix de 1,5 n'est pas optimal (net maximal vers 1,8) ; il est juste un point intermédiaire figé avant le test. Rappel : `eMax=0.9` donne 72,6 % / PF 3,6 / 514 trades en dév. (non testé sur l'année de test).

## 7. Réserves (à lire)

1. **Ampleur suspecte.** 77 % de gagnants et PF > 5 sur 3 ans pour une entrée à 15 min est très au-dessus du 44 (57 % / 1,35). Je n'ai pas trouvé de fuite : les Dashator 60/240 utilisent la bougie clôturée (`[1]` + lookahead_on, réglage par défaut « sans repaint ») ; l'effet est le même les 4 quarts d'heure d'une heure et ne décroît pas avec la position dans la bougie 4 h ; il tient sur 4 semestres, les deux sens, les 5 jours, 12 trimestres. Mais je n'ai pas les bougies et je ne peux pas le prouver. **Le test décisif est un vrai backtest TradingView de la ligne ci-dessus** (la fenêtre de 3 ans) puis un suivi en réel/papier : s'il sort ≪ 70 %, c'est une fuite ou un artefact du journal (graphique HA, remplissage au prix HA).
2. Le journal n'a qu'une position à la fois : le vrai run aura ~20 % de trades en plus (population un peu différente, probablement un peu moins bonne : cf. écart 40/44).
3. n = 491 sur le journal : pas de marge sur le plancher de 500 ; l'alternative règle ce point.
4. La recherche a été menée sur 2 ans et le test est un seul tirage de 143 trades (IC 95 % du % gagnants : 70 à 84).
5. Les chiffres propfirm supposent les trades du journal indépendants du jour et ne retirent pas les trades qui traversent la clôture CME (option nuit="exclure" du simulateur non testée).
