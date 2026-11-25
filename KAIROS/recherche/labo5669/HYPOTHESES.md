# Hypothèses — Relevé complet (écrites AVANT d'être testées)

Protocole commun : construction 2019-2022, contrôle 2023-2024, scellé 2025-2026 fermé. Moteur
`complet/moteur.py` (règles Strat5669, 2 contrats, 1,25 $ par côté, 1 tick de glissement, stop d'abord).
Hasard au même nombre de trades, mêmes heures (référence A : sens au hasard, même part de longs).
Chaque test va au registre avec le nombre d'essais cumulé ; correction de Bonferroni par famille.
Une hypothèse est retenue seulement si p < seuil corrigé en construction ET en contrôle.

**Critère ajouté le 19/11 (après le rejet de M1, décision DAEMON), pour tout ce qui suit :** P&L net
positif (coûts compris) en construction ET en contrôle, en plus de battre le hasard (réf. A) et la
référence « long seulement » (réf. L, dérive haussière) avec correction des tests multiples.

## C1 — Témoin « tout ou rien » (écrit le 19/11, avant le test)
- Cible : résultat en R (P&L par contrat, coûts compris, divisé par le risque 2 ATR × valeur du point)
  d'un trade décidé à la clôture de chaque bougie, dans chaque sens, géométrie FIXE : stop 2 ATR,
  objectif 1 R, sortie au temps 16 bougies, sorties `fin` comprises.
- Variables : les 25 champs numériques de la fiche (sauf dt et les prix bruts), les 35 bits, plus
  quelques dérivés sans prix bruts : (h − l) / ATR, (c − o) / ATR, rendements sur 4 et 16 bougies / ATR,
  heure de Paris, jour de la semaine.
- Modèle : gradient boosting (HistGradientBoostingRegressor, 300 itérations max, taux 0,05, 31 feuilles,
  200 exemples par feuille minimum, arrêt précoce sur les 20 % les plus récents de 2019-2022).
  Un modèle par instrument et par sens.
- Mesures sur 2023-2024 : corrélation de rang (Spearman) prédiction / résultat ; R moyen par décile
  de prédiction.
- Stratégie témoin : entrer quand la prédiction dépasse son 98e centile mesuré sur la tranche
  d'arrêt précoce (sens à la plus forte prédiction si les deux passent), une position à la fois.
  2 tests (MNQ, MES) : seuil corrigé 0,025.
- Lecture : si le témoin ne trouve aucun avantage hors échantillon, les familles faites à la main
  ont peu de chances (elles utilisent les mêmes champs).

**Résultat C1 (19/11)** : aucun avantage hors échantillon (contrôle MNQ p = 0,056, MES p = 0,47 ;
corrélations de rang expliquées par le coût fixe en R). Voir registre C1-01, C1-02.

## Familles faites à la main (écrites le 19/11, avant le test)
Signal décidé à la clôture de la bougie i (champs de la fiche i), entrée à l'ouverture suivante.
Long et short en miroir ; si les deux sont vrais sur la même bougie, pas de trade. Pas d'entrée sur une
bougie `fin` (moteur). 2 000 tirages au hasard (réf. A). Moins de 30 trades en construction = non testé.
Seuil = 0,05 / nombre de tests de la famille ; le contrôle utilise 0,05 / nombre d'hypothèses retenues.

### F1 Tendance — géométrie fixe : stop 2 ATR, objectif 1,5 R, 16 bougies — 3 × 2 instruments = 6 tests (seuil 0,0083)
- T1 : TREND 1 h et 4 h haussiers (bits tr1h, tr4h) ET Dashator 1 h / 4 h terminés haussiers (k1 > 0, k4 > 0)
  ET flip Heishinator haussier (hei_L) : fin de repli dans la tendance.
- T2 : T1 ET TREND 15 min haussier ET Directionnor 4 h long (dirH = 1).
- T3 : T1 ET 0 ≤ e1 ≤ 1 (clôture HA au-dessus de l'EMA 50, à 1 ATR au plus : repli près de la moyenne).

### F2 Retour à la moyenne — géométrie fixe : stop 1,5 ATR, objectif 1 R, 8 bougies — 5 × 2 = 10 tests (seuil 0,005)
- M1 : climax d'achat sur la bougie (clx_L) → long ; climax de vente → short.
- M2 : divergence (div_L / div_S).
- M3 : pW ≤ −2 (close à 2 ATR ou plus sous le pivot weekly) ET hei_L → long ; pW ≥ 2 ET hei_S → short.
- M4 : Fibonacci. Swing haussier (fib_bas = 0) ET 0,5 ≤ fib ≤ 0,786 (repli de 50 à 78,6 %) ET hei_L
  → long ; swing baissier (fib_bas = 1) ET 0,5 ≤ fib ≤ 0,786 ET hei_S → short.
- M5 : zone Detector proche : detD ≤ 0,5 ATR ET hei_L → long ; detU ≤ 0,5 ATR ET hei_S → short.

### F3 Cassure — géométrie fixe : stop 2 ATR, objectif 1,5 R, 16 bougies — 3 × 2 = 6 tests (seuil 0,0083)
- B1 : cassure de trendline (tl_L / tl_S).
- B2 : cassure de niveau de séance ou Monday (lvl_L / lvl_S).
- B3 : (B1 ou B2) ET Feu ≥ 60 ET STRENGTH ≥ 60 → long ; (B1 ou B2 baissiers) ET Feu ≤ 40 ET STRENGTH ≤ 40 → short.

### F4 Filtre de régime — sur chacune des 11 hypothèses, géométrie de sa famille — 11 × 2 × 2 = 44 tests (seuil 0,00114)
- R1 : vr ≥ 1,2 (volatilité au-dessus de sa moyenne 96 bougies).
- R2 : ADX ≥ 25.

**Résultat F1-F4 (19/11)** : 65 tests sur 66 ne passent pas la construction. MNQ M1 (climax) passe le
critère d'alors (construction p = 0,0035, contrôle p = 0,0495) mais perd de l'argent dans les deux
périodes (−3 314 $, −1 465 $) et ne bat pas « long seulement » en contrôle (p = 0,084) : REJETÉ,
scellé fermé. C'est ce cas qui a fait ajouter le critère de P&L positif.

## Programme « objectifs de Jeremy » (écrit le 25/11, avant tout test)
Demande : Jeremy via DAEMON (25/11, 10h54). Objectifs jugés en lecture **alertes** uniquement :
(1) 40 % par an, soit un rapport gain annuel / pire creux ≥ 3 ; (2) prop firm : 6 % par mois presque tous les
mois, sans enfreindre une règle (FTMO 100k : 5 % par jour, 10 % au total ; Tradeify 50k : 2 000 $ EOD suiveur).

**Données.** Recherche : Relevés complets fiable/5min et fiable/15min (MNQ, MES), 17/10/2023 → 13/11/2026.
1re moitié (H1) → 01/05/2025 = choix ; 2de moitié (H2) = contrôle. H2 a déjà été vue dans l'étude des seuils du
25/11 : elle n'est donc qu'un contrôle partiel. **Examen** : export MNQ 5 min 01/01/2019 → 16/10/2023
(fiable/5min-avant/), SCELLÉ, ouvert une seule fois, après le gel des finalistes dans ce fichier (commit).

**Banc.** complet/moteur.py, une position à la fois par stratégie, entrée à l'ouverture suivante + 1 tick, stop + 1 tick,
1,25 $ par contrat et par côté. Décision du 56 : fiable/decision56.py. Score de fiabilité : tables fiable/seuils.py
apprises sur H1.

**Mesure de choix (H1 seulement).** Rapport R/C = P&L annualisé / pire creux (par contrat), avec au moins 60 trades et
un P&L > 0 sur H1. Pour éviter un pic isolé, chaque case est notée par la médiane de R/C sur elle et ses voisines
immédiates de la grille (k, R, N à ± 1 cran, même seuil). Le meilleur de chaque piste est retenu.

**Pistes.**
- A. MNQ 5 min, lecture b + score. Grille : stop k ∈ {1 ; 1,5 ; 2 ; 3 ; 4} × ATR ; objectif R ∈ {0,5 ; 0,667 ; 1 ; 1,5 ; 2} ;
  durée N ∈ {8 ; 16 ; 32 ; 64} bougies ; seuil de score ∈ {0 ; 60 ; 70 ; 80 %}. 400 cases.
- B. MNQ 5 min, lecture k (bougies 1 h / 4 h terminées, aucun fantôme), même grille de sorties, sans score : 100 cases.
- C. Sur la case retenue en A et en B : filtres Directionnor 4 h dans le sens (oui / non) × créneau (aucun ;
  09:00-12:00 + 15:30-18:00 Paris ; 09:00-22:00 Paris) × ADX (aucun ; ≥ 20 ; ≥ 25). 17 combinaisons par base, 34 cases.
- D. Combinaisons, 1 contrat par composante : D1 = MNQ 5 (meilleur de A ou C) + MNQ 15 min (sorties du 56, lecture b,
  seuil choisi sur H1 parmi 0 / 60 / 70 / 80 %) ; D2 = MNQ 5 + MES 15 min seuil 80 % (choisi le 25/11 en voyant les deux
  moitiés : signalé) ; D3 = les trois. 3 cases + 4 seuils MNQ 15.

**Finalistes.** 5 au plus : le meilleur de A, B, C, D, plus le suivant toutes pistes confondues s'il est distinct.
Contrôle sur H2 : P&L > 0 sur H1 et H2, et battre les références de hasard B et L sur H2 (1 000 tirages, mêmes
heures, même nombre de trades, mêmes sorties) avec p < 0,05 / nombre de finalistes. Le hasard sur H1 est donné pour
information (biaisé par le choix).

**Mesures des finalistes.** Taille maximale où le pire creux et le pire jour de la période de recherche restent sous
80 % des limites (FTMO 10 000 $ / 5 000 $ ; Tradeify 2 000 $ → 1 600 $) ; à cette taille : % par an, % par mois,
part de mois positifs, part de mois ≥ 6 %. Évaluations FTMO (phase 1 +10 %, phase 2 +5 %, 4 jours min) et Tradeify
(+3 000 $, consistance 40 %) depuis chaque jour de départ et en blocs de 5 jours (1 000 chemins de 250 jours) :
phase rapide à la taille maximale, phase financée à la moitié (part de mois ≥ 6 %, probabilité d'enfreindre une
règle en 12 mois).

**Résultat (25/11).** Sélection sur H1 : 541 cases. Meilleur R/C au plateau : A = seuil 80 %, stop 4 ATR, objectif
2 R, 64 bougies (R/C 1,29, au bord de la grille) ; B (lecture k) 0,25, presque rien ; C n'améliore pas A ; D3 (MNQ 5 +
MNQ 15 + MES 15) 2,31. Contrôle sur H2 : les 5 finalistes gagnent de l'argent (+1 157 à +2 436 $ par contrat) mais aucun
ne bat le hasard : p contre B de 0,13 à 0,25, contre L de 0,11 à 0,24, pour un seuil de 0,01. R/C sur H2 de 0,48 à 1,07.
**Aucun finaliste gelé ; l'examen 2019-2023 n'est pas ouvert** (il reste disponible pour une hypothèse future).
Objectifs : un R/C ≥ 3 n'est atteint par aucune case, même sur H1 (max 2,31, en combinaison) ; 6 % par mois avec
un creux sous 10 % demanderait un R/C proche de 7.

## H-ORACLE — prévoir la couleur finale du Dashator 1 h / 4 h (écrit le 25/11, avant tout test)
Idée de Jeremy, carte blanche du 25/11 11h17. L'avantage du graphique vient de la couleur FINALE (o) du Dashator 1 h /
4 h. Hypothèse : un modèle prévoit sign(o1) et sign(o4) mieux que la persistance (« la couleur en cours reste »).

**Population.** Bougies qui portent un déclencheur du 56 (bits sF / sM / hei / tl / lvl / clx / div), fiable/5min et
fiable/15min, MNQ et MES. Apprentissage sur H1 (17/10/2023 → 01/05/2025), test sur H2 (→ 13/11/2026).
**Cibles.** o1 > 0 et o4 > 0 (o = b de la dernière bougie du graphique dans la bougie 1 h / 4 h).
**Variables (connues à la clôture de la bougie signal).** b1, b4, part écoulée 1 h / 4 h ; chemin dans la bougie 1 h / 4 h
en cours (clôture − ouverture, plus haut − ouverture, ouverture − plus bas, en ATR du graphique) ; tous les champs
numériques et les 35 bits du Relevé complet de la bougie et des 3 précédentes (sauf les prix bruts) ; heure et minute.
**Modèle.** HistGradientBoostingClassifier, un par unité × instrument × 1 h / 4 h (8 modèles) ; 500 itérations max,
taux 0,05, 31 feuilles, 100 exemples par feuille min, arrêt précoce sur les 20 % les plus récents de H1.
**Référence « persistance ».** Signe de b ; probabilité = table de fiabilité (fiable/seuils.py, apprise sur H1).
**Métriques sur H2.** (1) précision et log-loss du modèle contre la persistance, pour o1 et o4 ; (2) gain de précision par
quart de part écoulée ; (3) calibration (déciles de probabilité) ; (4) **décision du 56** : sur les bougies où le reste du
56 est vrai (déclencheur sans opposé, pas `fin`, écart EMA ≤ 0,6), part de décisions égales à la décision du graphique
(lecture o), modèle (couleurs prévues) contre persistance (lecture b).
**Arrêt.** Si le gain de précision sur les décisions du 56 est inférieur à 2 points (moyenne des 4 cas unité ×
instrument), on s'arrête.
**Sinon (étape 4).** Décision du 56 avec les couleurs prévues (P ≥ seuil, seuil choisi sur des prévisions hors
échantillon de H1, validation croisée par blocs de temps), mesurée en alertes sur H2, une position à la fois, sorties du
56 : hasard A / B / L (1 000 tirages, seuil 0,05 / nombre de cas), R/C, % annuel, % mensuel, fantômes, trades nés après
coup. Examen 2019-2023 toujours scellé.

**Résultat H-ORACLE (25/11).** Sur H2, le modèle ne prévoit pas mieux la couleur finale que la persistance. Précision
o1 / o4 : de −0,9 à +0,02 point (5 min MNQ 1 h 88,99 % → 88,57 % ; 15 min MES 4 h 88,75 % → 87,88 %). Log-loss un peu
meilleure sur le 1 h (5 min MNQ 0,268 → 0,259), pas sur le 4 h. Aucun gain net par quart de part écoulée. Calibration
correcte (écart moyen 0,6 à 3,7 points). Décisions du 56 égales au graphique : persistance 85,8 à 92,1 %, modèle −1,30 à
+0,13 point, **moyenne −0,50 point** : sous le seuil de 2 points, ARRÊT. Étape 4 non faite, examen toujours scellé.

## H-SORTIE — couper un trade quand on SAIT qu'il est fantôme (écrit le 25/11, avant tout test)
Demande de Jeremy du 06/11 (« que les trades se stoppent immédiatement lorsqu'ils disparaissent au recalcul »), relayée
par DAEMON sous la carte blanche. La couleur finale de la bougie 1 h (puis 4 h) qui contient le signal est connue, sans
fuite, à sa clôture.

**Cas.** Lecture alertes (b), 56 d'origine (3 ATR, 0,667 R, 16 bougies), seuil de score 0 et 70 %, en 5 min MNQ,
15 min MNQ et 15 min MES. Fichiers fiable/, H1 (→ 01/05/2025) / H2 (→ 13/11/2026). Une position à la fois.
**Règles (stop, objectif et durée du 56 inchangés ; sorties au marché à l'ouverture suivante, 1 tick de glissement ;
stop / objectif testés d'abord dans chaque bougie).**
- S1 : à la clôture de la bougie 1 h qui contient la bougie signal, si sa couleur finale (o1) est contre le trade → sortie.
- S2 : S1, puis même règle à la clôture de la bougie 4 h du signal (o4), si le trade est encore ouvert.
- S3 : à la clôture de chaque bougie en position, si b1 ou b4 en cours est contre le trade → sortie.
- E1 : pas d'entrée au signal ; à la clôture de chaque bougie 1 h, s'il y a eu dans cette heure une bougie où le reste du
  56 est vrai (déclencheur sans opposé, pas `fin`, écart EMA ≤ 0,6) et que o1 et b4 de cet instant confirment ce sens
  (sens unique), et qu'aucun trade n'est ouvert → entrée à l'ouverture suivante, stop / objectif sur l'ATR de cet instant.
Soit 4 règles × 2 seuils × 3 cas = 24 tests (référence : le 56 sans règle, mêmes cas).
**Critère.** P&L > 0 sur H1 et H2, et battre le hasard B (sens du déclencheur) et L (long seulement) sur H2, avec les
mêmes règles de sortie appliquées aux entrées tirées au hasard (1 000 tirages, mêmes heures, même nombre de trades),
p < 0,05 / 24. Contrôle « sortie au hasard » (S1, S2, S3) : même nombre de sorties anticipées, au même moment (même
bougie de contrôle pour S1 / S2, même décalage pour S3), mais sur des trades tirés au hasard parmi ceux encore ouverts ;
l'information compte si moins de 5 % des tirages font aussi bien. Mesures : R/C, % annuel (taille FTMO 100k dans les
règles), nombre de sorties anticipées. Examen 2019-2023 toujours scellé.

**Résultat H-SORTIE (25/11).** Aucune des 24 règles ne passe. Seules S1 / S2 / S3 en 5 min MNQ à 70 % gagnent sur H1 et
H2, mais moins que le 56 seul (S1 : +654 / +2 895 $ par contrat contre +1 140 / +3 031 $), et le hasard B / L sur H2 donne
p de 0,004 à 0,021 pour un seuil de 0,05 / 24 = 0,002. La sortie anticipée sur la couleur finale ne fait pas mieux qu'une
sortie au hasard au même moment (p de 0,24 à 1,00) : couper le fantôme à la clôture 1 h / 4 h réalise une perte déjà
engagée et coupe autant de trades qui se seraient rétablis. S3 dégrade partout ; E1 perd partout (5 min MNQ H2 −3 210 $,
15 min MNQ H2 −5 440 $) : entrer après confirmation arrive trop tard. Examen toujours scellé.

## EXAMEN-1 — hypothèse GELÉE (écrite le 25/11 avant le dépôt de l'export, décision DAEMON)
- **Règle** : 56 en lecture alertes (b), MNQ 5 min, score de fiabilité p1 × p4 ≥ 70 % avec les tables 5 min de 2c79a6a
  (identiques à Strat5669_FIABLE a9301a8), FIXES, jamais réapprises ; part écoulée calculée comme le Pine (heure de Paris) ;
  score inconnu = pas de trade. Sorties du 56 : 3 ATR, 0,6667 R, 16 bougies. Une position à la fois, 2 contrats,
  1,25 $ par contrat et par côté, moteur complet/moteur.py.
- **Données** : Relevé complet MNQ 5 min du 01/01/2019 au 16/10/2023, jamais vu (KAIROS-data/fiable/5min-avant/). En
  plusieurs morceaux : concaténés, doublons d'horodatage retirés, rien d'autre. Décisions du 07/01/2019 (une semaine de
  mise en route) au 16/10/2023 00:00 exclu.
- **Critère de succès, un seul test, α = 0,05** : P&L > 0 ET p_B < 0,05 ET p_L < 0,05 (moteur.hasard, 1 000 tirages,
  graine 5669, mêmes heures, même nombre de trades, mêmes sorties ; p = (tirages ≥ P&L + 1) / 1 001).
- **Rapporté, hors critère** : R/C, % annuel à la taille FTMO 100k dans les règles, P&L par année, fantômes.
- **Aucun réglage modifié après avoir vu les données.** Script gelé : fiable/examen1.py (même commit). Essai à blanc sur
  les données de recherche (pas l'export) : 319 trades, +8 326 $, fantômes 21 %, identique à 2c79a6a.

**EXAMEN-1 SUSPENDU (25/11, 11h36)** : consigne de Jeremy, exclusivement MNQ et MES et données de 2023 à aujourd'hui ;
pas d'export 2019-2023. L'hypothèse et le script restent gelés (7f0c2d8), jamais exécutés sur des données d'examen.

## Programme 5 min — familles F1-F5 et témoin C1 (écrit le 25/11, avant tout test)
Consigne de Jeremy (11h36) : MNQ et MES seulement, 17/10/2023 → 13/11/2026 (fiable/5min). Plus de période jamais vue.
**Protocole.** H1 (→ 01/05/2025) = sélection, H2 = contrôle. Lecture alertes (b) ou bougie terminée (k), jamais o : les
champs du Relevé complet sont tous sans fuite. Moteur complet/moteur.py, une position à la fois, 2 contrats.
Références de hasard B (sens du déclencheur) et L (long seulement), 1 000 tirages, mêmes heures, même nombre de trades.
- **H1** : candidat si au moins 30 trades, P&L > 0, p_B et p_L < 0,05 / (nombre de tests de la famille). Pas de tirage si
  le P&L de H1 est ≤ 0 (le critère est alors déjà manqué).
- **H2** : P&L > 0, p_B et p_L < 0,05 / (nombre de candidats retenus sur H1), ET plateau : sur H2, la géométrie du
  candidat et ses 6 voisines (k ∈ {1 ; 1,5 ; 2 ; 3 ; 4} ATR, R ∈ {0,5 ; 0,667 ; 1 ; 1,5 ; 2}, N ∈ {8 ; 16 ; 32 ; 64}, ± 1 cran)
  ont au moins 5 cas sur 7 à P&L > 0 et un R/C médian > 0.
- Pour un candidat qui passe : R/C, % mensuel à la taille FTMO 100k dans les règles, part de mois positifs.
**Familles F1-F4.** Définitions et géométries (en bougies) identiques au 19/11 (complet/familles.py) : F1 T1-T3,
F2 M1-M5, F3 B1-B3, F4 = les 11 avec R1 (vr ≥ 1,2) ou R2 (ADX ≥ 25). 66 tests.
**Famille F5, entrées seules** (stop 2 ATR, objectif 1 R, 16 bougies), long / short en miroir :
SF flèche Signator forte ; SM flèche moyenne ; HEI flip Heishinator ; DIR Directionnor du graphique qui passe à 1 / −1 ;
DIRH Directionnor 4 h qui passe à 1 / −1 ; PIV pW ≤ −2 / ≥ 2 seul ; FIB swing haussier / baissier et 0,5 ≤ fib ≤ 0,786
seul ; DET detD ≤ 0,5 / detU ≤ 0,5 seul ; DK Dashator 1 h terminé (k1) qui change de signe dans le sens de k4.
9 × 2 instruments = 18 tests.
**Témoin C1** en 5 min : même modèle qu'au 19/11 (gradient boosting, tous les champs, cible R à stop 2 ATR, 1 R,
16 bougies), appris sur H1 (arrêt précoce sur ses 20 % les plus récents), stratégie au 98e centile, contrôle sur H2.
2 tests.

**Résultat programme 5 min (25/11).** Familles F1-F5, 84 tests : **aucun candidat sur H1**. 75 tests perdent de l'argent
sur H1 ; les entrées seules (F5) perdent toutes lourdement (ex. PIV MNQ −86 958 $, DET MNQ −61 383 $ par contrat : en
5 min, le coût par trade écrase le signal). Le plus proche : MNQ M1 climax + ADX ≥ 25, H1 +1 622 $, p_B = p_L = 0,003 pour
un seuil de 0,0011 (même famille que le candidat formel rejeté le 19/11). Témoin C1 : très bon dans l'échantillon (H1 MNQ
+35 952 $, MES +19 492 $) puis effondré sur H2 (MNQ +1 732 $, p_B 0,034, p_L 0,052 ; MES −890 $) pour un seuil de 0,025 :
sur-apprentissage, rien hors échantillon. Aucun contrôle H2 de famille n'a eu lieu (pas de candidat).

## CLX-ADX — hypothèse UNIQUE sur H2 (écrite le 25/11 avant le test, décision DAEMON)
Règle telle quelle, choisie sur H1 seulement (meilleur des 84 tests du programme 5 min, jamais regardée sur H2) :
MNQ 5 min, climax d'achat (clx_L) → long, climax de vente (clx_S) → short, si ADX ≥ 25 sur la bougie signal ; pas de
trade si les deux ; géométrie F2 (stop 1,5 ATR, objectif 1 R, 8 bougies) ; une position à la fois, 2 contrats, moteur
complet/moteur.py. Période : décisions du 01/05/2025 au 13/11/2026 (H2).
Critère, un seul test : P&L > 0 ET p_B < 0,05 ET p_L < 0,05 (moteur.hasard, 1 000 tirages, graine 5669).
Rapporté hors critère : gain par trade et par contrat, R/C, % annuel à la taille FTMO 100k dans les règles, mois positifs.
**Résultat CLX-ADX (25/11) : ÉCHOUÉ.** H2 : 1 701 trades, 49,0 % gagnants, −11 215 $ (2 contrats), p_B 0,29, p_L 0,19 ;
−3,30 $ par trade et par contrat, pire creux 14 496 $, R/C −0,50, 7 mois positifs sur 19.

## Programme NIVEAUX / HORIZON (écrit le 25/11, avant tout test) — 52 tests
Carte blanche de Jeremy (11h44). MNQ et MES, fiable/5min et fiable/15min, 17/10/2023 → 13/11/2026, champs sans fuite
(b / k, jamais o). H1 (→ 01/05/2025) = sélection, H2 = contrôle. Une position à la fois, 2 contrats, 1,25 $ par côté.

### P1 — réaction aux niveaux (36 tests)
Niveaux reconstitués exactement : pivots P weekly / mensuel / annuel, prix = close − pW × ATR (idem pM, pA ; ATR des
vrais prix, comme RELEVE_COMPLET f_dr). Bande de contact x = 0,1 ATR. Les cassures de niveaux de séance et de trendlines
(bits lvl, tl) sont déjà testées (B1, B2 du 19/11 et du programme 5 min) : non reprises.
- **PIV-R (rejet)** : bougie dont le plus bas touche la bande d'un pivot (W, M ou A) avec clôture précédente et clôture
  au-dessus du pivot → long ; miroir au-dessus → short.
- **PIV-C (cassure)** : clôture précédente sous un pivot et clôture au-dessus de pivot + 0,1 ATR → long ; miroir → short.
- **DET-R (rejet Detector, proxy à la clôture)** : detD ≤ 0,25 et bougie haussière (c > o) → long ; detU ≤ 0,25 et bougie
  baissière → short.
- Contexte, 1 au maximum : aucun ; Dashator 4 h terminé dans le sens (k4) ; Directionnor 4 h dans le sens (dirH).
3 événements × 3 contextes × 2 instruments × 2 unités (5, 15 min) = 36. Sortie testée : stop 1,5 ATR, objectif 1,5 R,
16 bougies (centre de la grille stop {1 ; 1,5 ; 2} × R {1 ; 1,5 ; 2} × N {8 ; 16 ; 32}).

### P2 — biais du jour en lecture terminée, séance US (16 tests)
- Biais : long si k4 > 0 ET Directionnor terminé = 1, short si k4 ≤ 0 ET Directionnor = −1, sinon rien. Deux variantes :
  Directionnor 4 h (dirH) ou 1 h (dirM).
- Entrée, deux variantes : (a) heure fixe, décision à la clôture de la bougie qui finit à 08:45 Chicago (ouverture US +
  15 min) ; (b) première bougie entre 08:30 et 14:00 Chicago portant un déclencheur du 56 (sF / sM / hei / tl / lvl / clx /
  div) dans le sens du biais. Entrée à l'ouverture suivante, 1 trade par jour et par instrument.
- Sortie : à la clôture de la bougie qui finit à 15:00 Chicago (fin de séance US), remplie à l'ouverture suivante, ou
  sortie `fin`, ou stop à k ATR du graphique (5 min : k = 8 ; 15 min : k = 4). Pas d'objectif.
2 biais × 2 entrées × 2 instruments × 2 unités = 16.

### Critères
- **H1** : au moins 30 trades, P&L > 0, p_B et p_L < 0,05 / 36 (P1) ou 0,05 / 16 (P2), 2 000 tirages (moteur.hasard,
  mêmes heures, même nombre de trades, mêmes sorties). Pas de tirage si P&L H1 ≤ 0.
- **H2** : P&L > 0, p_B et p_L < 0,05 / (nombre de candidats H1), ET plateau sur H2 : P1, la sortie centrale et ses
  6 voisines de la grille, au moins 5 sur 7 à P&L > 0 et R/C médian > 0 ; P2, stop {bas, centre, haut} (5 min 4 / 8 / 12,
  15 min 2 / 4 / 6) × décalage de l'entrée {−30 min, 0, +30 min} (a) ou du début de fenêtre {08:00, 08:30, 09:00} (b),
  au moins 6 sur 9 à P&L > 0 et R/C médian > 0.
- Finaliste : % annuel à la taille FTMO 100k et Tradeify 50k dans les règles, % mensuel, mois positifs, R/C, évaluations
  FTMO / Tradeify depuis chaque jour de départ (phase rapide à la taille maximale, phase financée à la moitié).

**Résultat NIVEAUX / HORIZON (25/11).** 52 tests, **aucun candidat sur H1**. 39 perdent de l'argent sur H1. Le rejet
Detector perd partout et lourdement (5 min MES −52 022 $ par contrat). Les seuls P&L positifs en MNQ viennent du contexte
k4 (4 h terminé dans le sens) ; le meilleur, 15 min MNQ cassure de pivot + k4, fait H1 +6 723 $ (188 trades) avec p_B 0,025
et p_L 0,008, pour un seuil de 0,0014. P2 (biais terminé, séance US) : meilleur 5 min MES biais 4 h, première entrée,
H1 +4 592 $, p_B 0,16. Pas de contrôle H2 (aucun candidat), pas de simulation de prop firm.
