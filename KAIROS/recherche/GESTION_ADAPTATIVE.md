# Gestion adaptative — spécification commune Pine / Python (17/10/2026)

Demande de Jeremy : stop et objectif NON fixes, choisis à l'entrée selon la situation ; le plus de trades
gagnants possible ; objectif toujours entre 1R et 2R ; bon PnL pour la propfirm (Tradeify Select Flex).
La même règle est codée dans `STRATEGIE_V1.pine` (mode « Adaptatif ») et dans
`recherche/adaptatif/` (Python, moteur commun). Toute différence entre les deux est un bug.

Tout est calculé à la CLÔTURE de la bougie signal, sans donnée future. Prix = vrais prix (`r_*`), ATR = ATR 14
des vrais prix (`r_atr`). `dir` = +1 long, −1 short. `e` = prix d'entrée estimé (clôture du signal).

## 1. Score de confluence C (0 à 3)
- +1 si le TREND de l'unité supérieure (60 min par défaut, réglable 4 h) va dans le sens du trade ;
- +1 si la part du Feu de Confluence dans le sens du trade ≥ `adFeu` (60 %) ;
- +1 si ADX 14 ≥ `adAdx` (25) ET DI+ > DI− pour un long (DI− > DI+ pour un short).

## 2. Stop
- Volatilité relative `vr = r_atr / SMA(r_atr, 96)` (96 bougies = 1 jour en 15 min).
- k = `adKbas` (2,5) si vr < 0,8 ; `adKhaut` (1,5) si vr > 1,3 ; sinon `adK` (2,0). Stop = e − dir × k × ATR.
- Variante « stop sur niveau » (`adNiv` = 1) : si un niveau de protection (familles du groupe 3b, priorité
  du réglage) est derrière l'entrée entre `slMin` et `slMax` ATR (1 et 3 par défaut), stop derrière lui
  (marge `slMarge`) ; sinon le stop ATR ci-dessus.
- Risque R = |e − stop|.

## 3. Objectif
- Objectif de base selon C : C ≤ 1 → `adR1` (1,0 R) ; C = 2 → `adR2` (1,5 R) ; C = 3 → `adR3` (2,0 R).
- Obstacle : le niveau ADVERSE le plus proche devant le prix (familles d'objectif du groupe 3b), moins la
  marge `tpMarge`, à la distance D.
  - si D < 1,0 R : trade NON PRIS (pas la place d'aller chercher 1R) — réglage `adSaute` (1 = oui) ;
  - si 1,0 R ≤ D < objectif de base : objectif = l'obstacle (on encaisse avant lui) ;
  - sinon : objectif de base.
- L'objectif est donc toujours entre 1R et 2R.

## 4. Taille et sortie
- Risque fixe en $ par trade (le stop varie) ; à plat avant 15:59 Chicago ; pas de break-even par défaut.

## Paramètres et défauts
`adFeu=60 ; adAdx=25 ; adK=2 ; adKbas=2.5 ; adKhaut=1.5 ; adR1=1 ; adR2=1.5 ; adR3=2 ; adNiv=0 ; adSaute=1`
