# Biais global puis déclencheurs — spécification commune Pine / Python (17/10/2026)

Idée de Jeremy : les tableaux donnent la DIRECTION (biais global) ; on prend ensuite TOUS les signaux dans
ce sens (flèches Signator Fort et Moyen, Heishinator, cassures, climax) si quelques conditions de qualité sont
réunies. But : beaucoup plus de trades que le préréglage 25, avec un bon taux et un bon PnL propfirm.
Codé dans `STRATEGIE_V1.pine` (groupe « 1b. BIAIS GLOBAL ») et dans `recherche/biais/` (Python).

Tout à la CLÔTURE de la bougie signal ; multi-unités sur la dernière bougie CLÔTURÉE de chaque unité
(comme le tableau TIMEFRAME de CompletV3, sans repaint).

## 1. Votes (+1 haussier, −1 baissier, 0 neutre)
**Bloc FOND — unités 1 h, 4 h, 1 jour (9 voix)** :
- TREND (close > EMA50) sur 60, 240, 1D ;
- Dashator (bougie Heiken Ashi haussière) sur 60, 240, 1D ;
- STRENGTH (0-4 : close>open, MACD>signal, close>EMA50, RSI>50) sur 60, 240, 1D : ≥ 3 → +1, ≤ 1 → −1, 2 → 0.

**Bloc INTRADAY (11 voix)** :
- TREND et Dashator sur 5 et 15 min (4 voix) ;
- les 7 lignes INDICATOR | SIGNAL de CompletV3 (SuperTrend, EMA50, VWAP, régression linéaire, CPR, ORB,
  PDH/PDL), avec leur vote ±1 ou 0.

Score fond `F` = somme / 9, score intraday `I` = somme / 11 (entre −1 et +1).

## 2. Biais
- Biais HAUSSIER si `F ≥ bF` et `I ≥ bI` → seuls les LONGS sont permis.
- Biais BAISSIER si `F ≤ −bF` et `I ≤ −bI` → seuls les SHORTS.
- Sinon : pas de trade.
Défauts : `bF = 0,33` (au moins 6 voix sur 9 dans le sens, net +3), `bI = 0,2`.

## 3. Déclencheurs (dans le sens du biais seulement)
Union : flèche Signator Fort OU Moyen, flip Heishinator, cassure de trendline, cassure de session / Monday,
climax (BUY pour un long, SELL pour un short).

## 4. Qualité (réglages, chacun activable)
- Detector : place jusqu'à la zone opposée ≥ `detK` × ATR (défaut 1,5) ;
- climax : pas de trade contre le dernier climax ;
- blackout d'annonces.

## 5. Gestion (point de départ, celle du préréglage 25)
Stop 2 ATR, objectif 1,5 R, sortie après 8 bougies, fenêtre 00:20-22:15 Paris, à plat 15:59 Chicago.
