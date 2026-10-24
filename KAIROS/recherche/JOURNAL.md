# Mode JOURNAL — format du commentaire d'entrée (STRATEGIE_V1.pine V13, 17/10/2026)

But : le graphique TradingView ne charge que ~3 mois de bougies, mais le **backtest profond** d'une
stratégie couvre 3 ans. En mode journal (clé `jr=1`, préréglage « 99 JOURNAL »), la stratégie prend TOUS
les signaux des deux sens, sans biais ni filtre (seules la fenêtre 00:20-22:15 Paris et la clôture 15:59
Chicago restent), et écrit l'état des tableaux dans le commentaire de chaque entrée. L'export xlsx du
testeur (feuille « Trades », colonne « Signal » des lignes « Entrer … ») donne donc, pour 3 ans de trades,
la situation complète à l'entrée + le résultat (P&L, MFE, MAE, raison de sortie, durée).

Gestion du préréglage 99 : stop 2 ATR, objectif 1 R, sortie après 8 bougies, 2 micros (la même que le 40/44).

## Format (champs séparés par « | »)
`L|FH|F5|I3|f62/31|t110111|d101101|s3342|a24+|z2.3|e1.2|v0.95|c1|R37.50`

| Champ | Sens |
|---|---|
| `L` / `S` | sens du trade |
| 2e champ | déclencheurs présents sur la bougie signal, dans le sens du trade : F = Signator Fort, M = Signator Moyen, H = flip Heishinator, T = cassure de trendline, N = cassure de niveau (sessions / Monday), C = climax, D = divergence après excès |
| `F` | biais FOND en voix nettes (−9 à +9) = `bi_F × 9` (TREND, Dashator, STRENGTH sur 1 h, 4 h, 1 j) |
| `I` | biais INTRADAY en voix nettes (−11 à +11) = `bi_I × 11` |
| `f` | Feu de Confluence : % long / % short (29 voix) |
| `t` | TREND sur 3, 5, 15, 60, 240, 1D (1 = haussier) |
| `d` | Dashator sur 1, 5, 15, 60, 240, 1D (1 = bougie HA haussière) |
| `s` | STRENGTH (0-4) sur 15, 60, 240, 1D |
| `a` | ADX 14 arrondi, suivi de + (DI+ > DI−) ou − |
| `z` | place jusqu'à la zone Detector opposée la plus proche, en ATR (9.9 = aucune) |
| `e` | écart (clôture HA − EMA50) en ATR, signé |
| `v` | volatilité relative ATR / moyenne 96 bougies |
| `c` | dernier climax : 1 = BUY, −1 = SELL, 0 = aucun |
| `R` | risque du trade en points (distance du stop) → MFE/MAE en R = USD / (R × valeur du point × contrats) |

## Limites
- Une seule position à la fois : un signal qui arrive pendant un trade n'est pas journalisé. Un filtre
  rejoué sur le journal n'est donc pas exactement la stratégie filtrée ; à vérifier en comparant le
  sous-ensemble « biais 40 » du journal avec l'export réel du préréglage 40 / 44.
- Les MFE/MAE ne disent pas dans quel ordre le prix a touché les niveaux.
