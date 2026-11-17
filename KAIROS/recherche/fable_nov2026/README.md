# Scripts d'analyse de DAEMON (Fable 5.2), 15-17 novembre 2026

Copie des scripts jetables qui ont servi aux analyses des 15, 16 et 17/11/2026. Ils lisent les exports du
testeur TradingView déposés par Jeremy dans `~/ERGON/KAIROS-data/` et écrivent leurs fichiers `.pkl` dans
le dossier courant. Lancer avec : `uv run --quiet --with pandas --with openpyxl --with yfinance python -I <script>`.
Les chemins de données sont écrits en dur en tête de chaque script : les adapter avant de relancer.

| Script | Ce qu'il fait |
|---|---|
| `rl.py` | Chargeur commun des exports `.xlsx` (feuilles Trades et Propriétés) ; lit aussi le commentaire clé=valeur des relevés R16 / R48 → `rech.pkl` |
| `sf.py` | Exports Strat5669_SANSFUITE (modes a, b, ancien) → `sf.pkl` |
| `leak.py`, `dash.py`, `yf.py` | Preuve de la fuite : Dashator 1 h / 4 h recalculé sur bougies Yahoo, comparé aux alertes et à l'historique |
| `r1.py`, `r2.py`, `r3.py` | Relevés R16 / R48 : contrôle, effet de chaque variable, modèle appris sur 2023-2024 et testé sur 2025-2026 |
| `fin.py`, `opt.py`, `ex.py` | Heures d'entrée, sorties de fin de séance, autres stops et objectifs sur les vrais trades |
| `mc.py`, `mc2.py` | Probabilité de valider une éval 50k (objectif 3 000 $, plancher suiveur 2 000 $) |
| `pub.py`, `mom.py` | Bougies 1 h publiques (NQ=F, ES=F, 2,4 ans) : tendance 1 h / 4 h, 12 stratégies intraday classiques |
| `sol.py`, `ctx.py` | Sortie quand la bougie 1 h / 4 h se retourne ; filtres de contexte journalier |
| `fade.py` | CONTIENT UN BUG CONNU : lit un prix futur pour les entrées après 18:00 New York. Gardé comme exemple à ne pas refaire |
| `sweep.py` | Balayage des variantes dans la lecture « calcul d'origine » (valeur finale des bougies 1 h / 4 h) |
| `plus.py` | Tableau de synthèse d'un dossier d'exports (réussite, PF, P&L, baisse max, pire jour, par an) |
| `diff.py` | Comparaison trade par trade LucidBot V2 / Strat5669 |

Résultats et conclusions : mémoire `passation-fable.md` et `biais-futur-backtest.md`.
