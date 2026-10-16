# Préréglages à tester au testeur TradingView (3 ans) — SL « niveau de protection » et TP « prochain niveau »

Date : 16/10/2026. Scripts : `tools/strategie/preregles/` (voir la fin). **Ce sont des HYPOTHÈSES à valider
au testeur** : nos barres intraday ne couvrent qu'environ 2 mois (MESZ/NQZ sept.-oct. 2026, MES1! avr.-juil.
sans volume), soit 20 trades « A » en position unique. Aucun chiffre ci-dessous n'est une preuve.

## 1. Ce que disent les données (résumé)

**Le pivot de l'indicateur est calculé sur la bougie Heiken Ashi de la période.** L'API donne le pivot
annuel 2026 de NQ1! : P 21675,03 / R1 27114,66 / S1 16951,06, d'où H = 26399,00 (vrai plus haut, au tick),
L = 16235,40 et C = 22390,69 (pas au tick : open et close HA). CompletV3 fait pareil (request.security sur le
graphique HA). Ces niveaux « HA » ne sont pas ceux que le reste du marché regarde (pivots standard). Les deux
versions ont été testées (HA et « vrais prix »).

**1. Le prix ne réagit pas plus aux niveaux qu'à un niveau quelconque** (`reaction.py`). Un test, c'est le
prix qui vient à 0,1 ATR d'un niveau après s'en être éloigné de 0,5 ATR. Le rebond, c'est 1 ATR de reprise
avant 0,5 ATR de traversée. On compare avec des placebos : les mêmes niveaux décalés de ±1,6 et ±2,7 ATR
(±30/70 % du pas pour les ronds).
En 15 min, pour TOUTES les familles (pivots weekly/mensuels HA et vrais prix, zones Detector, sessions
Asie/Londres/US, Monday, ronds de 100 et fins), le taux de rebond est de 34-39 % contre 35-41 % au placebo.
Les écarts restent entre −0,04 et +0,04, et aucun IC 95 % par famille (bootstrap par jour) n'exclut 0. Mêmes résultats
en 30 et 60 min (d'août à octobre), sur MES comme sur NQ.
Une fois le niveau touché, le prix va au moins 0,25 ATR au-delà dans 72 % des cas, au placebo comme au
réel : **un stop placé 0,25 ATR derrière un niveau n'est pas mieux protégé**. La cassure franche (clôture à
1 ATR au-delà) n'est pas non plus plus rare. Le pivot annuel n'est jamais touché en 15 min. En 30/60 min,
il y a 38 tests (NQ, août) : 24 % de rebond contre 22 % au placebo.

**2. SL adaptatif** (`sl_tp.py`, `synthese.py`). On a comparé 224 variantes (7 priorités × 4 fourchettes ×
2 marges × base HA/vrais prix × repli ATR 2 ou trade sauté) aux stops fixes (1 à 3 ATR, points fixes), sur
les mêmes entrées. Coûts : 1 tick/côté + 1,25 $/contrat/côté.
- Sur 1003 entrées au hasard avec sortie Heishinator, 3 variantes ont un IC > 0 et 53 un IC < 0
  (moyenne −0,03 R). La meilleure sur MES finit 146e sur 224 sur NQ.
- Sur les signaux, l'image est la même ; la meilleure sur MES perd 0,13 R sur NQ.
- Le pivot seul (1-3 ATR) ne sert que dans 19 % des trades (weekly 13 %, mensuel 6 %, annuel 0 %). Il est
  neutre sur les entrées au hasard (−0,007 R [−0,02 ; +0,004]) et légèrement positif sur A (+0,08 R
  [+0,01 ; +0,16], n = 65) : une variante parmi beaucoup, à confirmer.
- Detector, sessions ou Monday en premier : neutre à négatif (A : −0,13 à −0,20 R).
- Stops fixes sur A : 2 ATR reste le meilleur, ici comme sur 3 ans. Au testeur (632 trades NQ), le stop
  à 1,5 ATR donne +0,03 R contre +0,16 R ; à 1 ATR, +0,03 R.

**3. TP adaptatif.** On a testé 312 variantes : jeux de niveaux, ratio minimum 1/1,5/2, « suivant » ou
« bloquant », repli Heishinator / 2R / trade sauté, avec ou sans Heishinator en plus.
- Seule tendance qui se retrouve sur les deux instruments : « objectif au prochain pivot HA ≥ 1,5 R ET sortie
  Heishinator ». Sur les entrées au hasard, +0,06 R [0,00 ; +0,12] (MES +0,04, NQ +0,13). Sur C, +0,21 R
  [+0,06 ; +0,41], mais n = 76. Sur A, −0,08 R [−0,49 ; +0,19].
- Un objectif sur niveau SANS Heishinator perd contre Heishinator sur les signaux (−0,03 à −0,20 R) et
  surtout sur A (−0,2 à −0,8 R). C'est cohérent avec les 3 ans : le gain de A vient de la queue, et tout
  objectif de 1 à 3 R ramène NQ de +0,16 à +0,01/+0,02 R.
- Pour l'objectif, les pivots « vrais prix » font moins bien que les pivots HA. Ajouter le Detector
  dégrade (−0,06 à −0,19 R).

**4. Trades A réels du testeur** (`trades_reels.py`).
- Les pivots de 2023-2025 ne peuvent PAS être reconstitués : l'historique du NQZ2026 d'avant sa cotation
  réelle ne colle pas au NQ1! ajusté (écart de 100 à 1300 points, incohérent dans un même mois). Il n'y a
  aucun journalier ES1!/NQ1!.
- À partir de juin 2026, NQ1! ajusté = Z2026 : 98 % des entrées tombent dans la bougie 1D du Z2026.
  Il reste 120 trades (57 NQ, 63 ES).
- Un pivot sous l'entrée à moins de 1 R : 33 trades. Ils ont été **plus** stoppés (64 % contre 48 %, écart
  +0,15 ; placebo +0,05, plage −0,06 à +0,15).
- Le plus bas atteint (MAE) s'arrête sur un pivot dans 5,0 % des trades (placebo 5,0 %). Le plus haut
  atteint (MFE) s'arrête juste sous un pivot dans 5,8 % des trades (placebo 5,3 %).
- **Rien n'indique que les pivots aient joué un rôle.** Pivot annuel : 1 seul trade concerné, impossible à
  tester.

**Conclusion pour l'idée de Jeremy.** Sur nos données, ni le stop derrière un niveau ni l'objectif sur
niveau ne battent un stop/objectif fixe de même taille : le niveau ne « retient » pas plus le prix qu'un
prix quelconque. Deux pistes restent à vérifier au testeur, sans risque de grosse dégradation :
- stop derrière un pivot SEULEMENT s'il se trouve entre 1 et 3 ATR, sinon 2 ATR ;
- objectif au prochain pivot HA ≥ 1,5 R, en GARDANT la sortie Heishinator.

## 2. Réglages communs (boîte de dialogue, non modifiables par un préréglage)

Graphique Heiken Ashi **15 min**, NQ1! puis ES1! (contrat continu ajusté, comme le 1er jet), 3 ans.
Mettre à la main :
- « TREND : unité » = **60** ;
- « Niveaux mesurés sur » = **Heiken Ashi (comme l'indicateur)** ;
- « Marges : unité » = **× ATR** (les marges 0.1 ci-dessous sont en ATR) ;
- « Niveaux ronds : intervalle » = **100** ;
- « Taille de position » = **Contrats fixes**, 1 contrat ;
- commission **1,25 $/contrat/côté**, glissement **1 tick** ;
- « Données multi-unités » = **Bougie clôturée (sans repaint)** ;
- blackout d'annonces : défauts (US 08:30 ET et 10:00 ET cochés) ;
- ATR (vrais prix) : 14.

Chaque préréglage = une ligne pour `f_pr_def()` (nom exact à ajouter aussi dans `options=[…]`). Toutes les
clés sont écrites, y compris les interrupteurs coupés.

Abréviation **BASE-A** (déclencheur A, à recopier en tête de ligne) :
`sens=Long seulement;clx=1;sig=0;hei=0;tl=0;lvl=0;tr=1;feu=0;ema=0;adx=0;det=0;clxF=0;bo=1;maxJour=3;be=0;trail=Aucun;oppArr=0;fin=0;part=0`

Abréviation **BASE-C** (déclencheur C) :
`sens=Les deux;clx=0;sig=0;hei=0;tl=1;lvl=0;tr=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=1;maxJour=3;be=0;trail=Aucun;oppArr=0;fin=0;part=0;hr=1;hr1On=1;hr1=1430-0800;hr2On=0`

**SL-PIV** (stop derrière un pivot HA entre 1 et 3 ATR, sinon 2 ATR) :
`stop=Niveau de protection;prio=annuel > mensuel > weekly;slA=1;slM=1;slW=1;slD=0;slMo=0;slSe=0;slRo=0;slMin=1;slMax=3;slMarge=0.1;atrK=2`

**TP-PIV** (objectif juste avant le 1er pivot HA à ≥ 1,5 R ; sinon pas d'objectif) :
`tp=Prochain niveau;tpA=1;tpM=1;tpW=1;tpD=0;tpMo=0;tpSe=0;tpRo=0;rrMin=1.5;tpMarge=0.1;tpSans=Pas d'objectif`

## 3. Les 19 préréglages, du plus prometteur au moins prometteur

Les résultats « nos données » viennent de `indicatif.py` : 15 min, position unique, 3 trades/jour au
plus, coûts inclus, $ pour 1 contrat MES / NQ (ES ≈ 10 × MES). ΔR = écart apparié à la référence (A2 pour
les A, C2 pour les C), IC 95 % par jours. « 3 ans » renvoie au 1er jet du testeur (A, R = 2 ATR).

| # | Nom (≤ 40 car.) | Pourquoi (1 phrase) | Résultat indicatif |
|---|---|---|---|
| 1 | `01 A jour 08-23h · SL 2 ATR · Heishi` | Garde A tel quel mais retire les entrées de nuit, négatives sur NQ et ES pendant les 3 ans. | Nos données : n 19, +0,68 R, PF 2,1 (MES +41 $, NQ +641 $). 3 ans : entrées 0-8 h perdantes sur NQ et ES. |
| 2 | `02 A réf · SL 2 ATR · Heishi` | Référence : A actuel, la seule entrée avec un léger avantage sur 3 ans (NQ). | Nos données : n 20, +0,61 R, PF 2,3 (MES +33 $, NQ +704 $). 3 ans : NQ +0,16 R, ES +0,06 R. |
| 3 | `03 A · SL pivots HA 1-3 ATR` | Stop derrière un pivot seulement s'il est à bonne distance (19 % des trades), sinon 2 ATR : peu de risque, une petite chance de gain. | n 20, +0,62 R, PF 2,3 ; ΔR +0,08 [+0,01 ; +0,16] (n 65, isolés). Hasard : −0,007 [−0,02 ; +0,004]. |
| 4 | `04 A · SL 2,5 ATR · Heishi` | Stop fixe prédéfini de référence ; 95 % des gagnants A ont une MAE < 1,06 R (2,1 ATR). | n 20, +0,44 R, PF 2,0 ; ΔR −0,16 [−0,50 ; +0,18]. |
| 5 | `05 A · SL 3 ATR · Heishi` | Stop fixe de référence, au bord de la zone utile 2,25-4 ATR de l'étude MAE/MFE. | n 20, +0,32 R, PF 1,7 ; ΔR −0,31 [−0,85 ; +0,20]. |
| 6 | `06 A · SL+TP pivots HA · Heishi` | Teste l'idée complète de Jeremy (stop et objectif sur pivots) sans perdre la queue grâce à la sortie Heishinator. | n 25, +0,50 R, PF 1,8 ; ΔR −0,01 [−0,36 ; +0,22]. |
| 7 | `07 A · SL 1,5 ATR · Heishi` | Stop fixe de référence plus serré. | n 24, +0,37 R, PF 1,0 ; ΔR +0,29 [−0,25 ; +0,81]. 3 ans : +0,03 R contre +0,16 (NQ). |
| 8 | `08 C · SL 2 ATR · TP pivots + Heishi` | Combinaison objectif pivot + Heishinator, la meilleure sur C et sur le hasard ; C est à refaire de toute façon (bug du 1er jet). | n 66, +0,11 R, PF 2,6 (MES +2 $, NQ +1326 $) ; isolés : +0,21 R [+0,06 ; +0,41] contre Heishi seul. |
| 9 | `09 C réf · SL 1,5 ATR · 2R` | Référence C du 1er jet, invalidée par le bug, jamais testée sur 3 ans. | n 60, +0,08 R, PF 4,0 (MES −4 $, NQ +1691 $) ; MES −0,13 R, NQ +1,09 R (n 10). |
| 10 | `10 A · SL fixe 80 pts (NQ)` | Stop en points fixes (≈ 2 ATR aujourd'hui) : teste si l'ATR qui suit la volatilité vaut mieux. | Simulé avec 80 pts NQ / 13 pts MES : n 20, +0,40 R, PF 1,5 (NQ +378 $) ; ΔR −0,12 [−0,68 ; +0,34]. |
| 11 | `11 A · SL fixe 13 pts (ES)` | Même test sur ES (≈ 2 ATR de 15 min aujourd'hui). | Voir 10 (MES : n 11, +0,54 R, +35 $/MES). |
| 12 | `12 A · SL 1 ATR · Heishi` | Stop fixe de référence le plus serré. | n 29, −0,14 R, PF 0,9 ; ΔR −0,20 [−0,57 ; +0,37]. 3 ans : +0,03 R (NQ), −0,00 (ES). |
| 13 | `13 A · SL niveaux (défaut)` | Stop « niveau de protection » avec la priorité par défaut du Pine (tous les niveaux, 0,5-3,5 ATR). | n 24, +0,16 R, PF 0,9 ; ΔR −0,11 [−0,41 ; +0,17]. |
| 14 | `14 A · SL Detector d'abord` | Teste l'idée « Detector = zone qui bloque » pour protéger. | n 23, +0,29 R, PF 1,1 ; ΔR −0,03 [−0,23 ; +0,17]. Réaction Detector = placebo. |
| 15 | `15 A · SL Monday/sessions d'abord` | Les niveaux les plus souvent disponibles (sessions dans 45 % des trades). | n 23, +0,25 R, PF 1,1 ; ΔR −0,05 [−0,25 ; +0,14]. |
| 16 | `16 A · TP pivots HA + Heishi` | Objectif sur pivot sans toucher au stop, sortie Heishinator gardée. | n 25, +0,47 R, PF 1,7 ; ΔR −0,08 [−0,49 ; +0,19]. |
| 17 | `17 A · TP pivots+Detector + Heishi` | Variante de Jeremy avec les zones Detector opposées comme objectif. | n 26, +0,42 R, PF 1,7 ; ΔR −0,11 [−0,65 ; +0,24]. |
| 18 | `18 A · TP fixe 3R` | Objectif fixe de référence, sans Heishinator. | n 25, +0,56 R, PF 2,3 ; ΔR −0,22 [−0,98 ; +0,49]. 3 ans : +0,02 R contre +0,16 (NQ). |
| 19 | `19 A · TP pivots ≥2R sinon rien` | Idée de Jeremy à l'état pur : objectif sur pivot, trade refusé s'il n'y a pas de place. | n 21, +0,28 R, PF 1,6 ; ΔR −0,68 [−1,99 ; +0,48]. Le plus risqué : coupe la queue de A. |

### Lignes `f_pr_def()` complètes

```
nom == "01 A jour 08-23h · SL 2 ATR · Heishi"   ? "BASE-A;hr=1;hr1On=1;hr1=0800-2300;hr2On=0;stop=ATR × k;atrK=2;tp=Aucun;oppHei=1" :
nom == "02 A réf · SL 2 ATR · Heishi"           ? "BASE-A;hr=0;stop=ATR × k;atrK=2;tp=Aucun;oppHei=1" :
nom == "03 A · SL pivots HA 1-3 ATR"            ? "BASE-A;hr=0;SL-PIV;tp=Aucun;oppHei=1" :
nom == "04 A · SL 2,5 ATR · Heishi"             ? "BASE-A;hr=0;stop=ATR × k;atrK=2.5;tp=Aucun;oppHei=1" :
nom == "05 A · SL 3 ATR · Heishi"               ? "BASE-A;hr=0;stop=ATR × k;atrK=3;tp=Aucun;oppHei=1" :
nom == "06 A · SL+TP pivots HA · Heishi"        ? "BASE-A;hr=0;SL-PIV;TP-PIV;oppHei=1" :
nom == "07 A · SL 1,5 ATR · Heishi"             ? "BASE-A;hr=0;stop=ATR × k;atrK=1.5;tp=Aucun;oppHei=1" :
nom == "08 C · SL 2 ATR · TP pivots + Heishi"   ? "BASE-C;stop=ATR × k;atrK=2;TP-PIV;oppHei=1" :
nom == "09 C réf · SL 1,5 ATR · 2R"             ? "BASE-C;stop=ATR × k;atrK=1.5;tp=En R;tpR=2;oppHei=0" :
nom == "10 A · SL fixe 80 pts (NQ)"             ? "BASE-A;hr=0;stop=Fixe (points);fixPts=80;tp=Aucun;oppHei=1" :
nom == "11 A · SL fixe 13 pts (ES)"             ? "BASE-A;hr=0;stop=Fixe (points);fixPts=13;tp=Aucun;oppHei=1" :
nom == "12 A · SL 1 ATR · Heishi"               ? "BASE-A;hr=0;stop=ATR × k;atrK=1;tp=Aucun;oppHei=1" :
nom == "13 A · SL niveaux (défaut)"             ? "BASE-A;hr=0;stop=Niveau de protection;prio=annuel > mensuel > detector > weekly > monday > session > rond;slA=1;slM=1;slW=1;slD=1;slMo=1;slSe=1;slRo=1;slMin=0.5;slMax=3.5;slMarge=0.1;atrK=2;tp=Aucun;oppHei=1" :
nom == "14 A · SL Detector d'abord"             ? "BASE-A;hr=0;stop=Niveau de protection;prio=detector > annuel > mensuel > weekly > monday > session;slA=1;slM=1;slW=1;slD=1;slMo=1;slSe=1;slRo=0;slMin=1;slMax=3;slMarge=0.1;atrK=2;tp=Aucun;oppHei=1" :
nom == "15 A · SL Monday/sessions d'abord"      ? "BASE-A;hr=0;stop=Niveau de protection;prio=monday > session > annuel > mensuel > weekly;slA=1;slM=1;slW=1;slD=0;slMo=1;slSe=1;slRo=0;slMin=1;slMax=3;slMarge=0.1;atrK=2;tp=Aucun;oppHei=1" :
nom == "16 A · TP pivots HA + Heishi"           ? "BASE-A;hr=0;stop=ATR × k;atrK=2;TP-PIV;oppHei=1" :
nom == "17 A · TP pivots+Detector + Heishi"     ? "BASE-A;hr=0;stop=ATR × k;atrK=2;tp=Prochain niveau;tpA=1;tpM=1;tpW=1;tpD=1;tpMo=0;tpSe=0;tpRo=0;rrMin=1.5;tpMarge=0.1;tpSans=Pas d'objectif;oppHei=1" :
nom == "18 A · TP fixe 3R"                      ? "BASE-A;hr=0;stop=ATR × k;atrK=2;tp=En R;tpR=3;oppHei=0" :
nom == "19 A · TP pivots ≥2R sinon rien"        ? "BASE-A;hr=0;stop=ATR × k;atrK=2;tp=Prochain niveau;tpA=1;tpM=1;tpW=1;tpD=0;tpMo=0;tpSe=0;tpRo=0;rrMin=2;tpMarge=0.1;tpSans=Ne pas prendre le trade;oppHei=0" :
```

**Dans le Pine, remplacer `BASE-A`, `BASE-C`, `SL-PIV` et `TP-PIV` par leur texte complet (§ 2)** : ce sont
des abréviations de ce document, pas des clés. Tant qu'un mode n'est pas actif, ses clés de niveaux
(`slX`, `tpX`, `prio`…) ne servent pas, ce qui est sans effet.

### Ordre de test conseillé

1. Lancer 02 (référence) puis 01 sur NQ1! et ES1!, et ne garder 01 que s'il fait mieux sur NQ, sur ES ET sur
   chaque moitié des 3 ans.
2. Ensuite 03, 06 et 16 sur la meilleure des deux bases : ce sont les seules variantes « niveaux » qui ont une
   chance raisonnable.
3. Les stops fixes 04, 05, 07, 10, 11 et 12 situent la référence. Au testeur, la sortie « Stop » donne
   directement le taux de stop.
4. Les préréglages 13 à 19 servent à confirmer, ou à réfuter, l'idée « Detector / pivots comme objectif ».
   Ils devraient faire moins bien que 02.
5. Pour comparer : R moyen et PF, et pas seulement le P&L total (un stop plus large augmente le risque en $
   par trade). Le testeur exporte la liste des trades ; `../testeur_1er_jet/` sait relire ces exports.

## 4. Limites

- Environ 2 mois de barres intraday, période haussière : les n vont de 19 à 76 par préréglage, et tous les IC
  sont larges. Le classement s'appuie surtout sur les résultats sur 3 ans de A et sur l'absence de réaction
  aux niveaux.
- Simulation : vrais prix reconstitués depuis le HA (fiables en 15 min), niveaux figés à la bougie du signal
  (comme le Pine). Sessions et Monday mesurés ici sur les vrais prix, alors que le Pine utilise le HA par
  défaut. Le stop « le plus proche toutes familles confondues » n'existe pas dans le Pine (la priorité y est
  un ordre de familles) : il a été testé, il ne fait pas mieux.
- Pivot annuel : il n'a jamais été touché sur nos barres, et les 3 ans de trades ne permettent pas de
  reconstituer ses niveaux. Seul le testeur (préréglages 03, 06, 13) peut dire s'il joue un rôle.

## 5. Fichiers

| Fichier | Rôle |
|---|---|
| `niveaux.py` | Niveaux par barre : pivots Y/M/W (HA et vrais prix, journalier 1D + agrégation intraday), Detector, sessions, Monday, ronds |
| `reaction.py` | Question 1 : rebond, cassure, pénétration au niveau contre placebo ; `sortie_reaction_15.txt`, `sortie_reaction_30-60.txt`, CSV |
| `sl_tp.py` | Questions 2 et 3 : simulation appariée de 232 stops × 3 sorties et 312 objectifs × 2 stops (caches `cache_sl.pkl`, `cache_tp.pkl`) |
| `analyse.py`, `synthese.py` | Tableaux appariés, apprentissage MES → validation NQ, contrôle du biais de sélection ; `sortie_synthese.txt` |
| `trades_reels.py` | Question 4 : trades A réels (juin → oct. 2026) face aux pivots ; `sortie_trades_reels.txt`, `trades_reels.csv` |
| `indicatif.py` | Résultat indicatif de chaque préréglage (position unique) ; `sortie_indicatif.txt`, `indicatif.csv` |
