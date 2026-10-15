# Optimiseur walk-forward de STRATEGIE_V1

Cherche **ensemble** le déclencheur, les filtres, l'entrée, le stop et la sortie de `STRATEGIE_V1.pine`,
en walk-forward glissant, en retenant une **zone stable** (pas un maximum isolé), avec correction du biais
de sélection (Deflated Sharpe, Reality Check de White, SPA de Hansen), bootstrap par jour, Monte Carlo de
ruine et un nombre minimum de trades hors échantillon (100 par défaut). Rapport Markdown en français avec
le bloc de réglages à recopier dans le Pine.

## Recréer l'environnement (le scratchpad est temporaire)

```bash
~/.local/bin/uv venv ~/venv-quant --python 3.12
~/.local/bin/uv pip install --python ~/venv-quant/bin/python -r tools/strategie/optim/requirements.txt
```

## Lancer

```bash
PY=~/venv-quant/bin/python
# exports d'un ou plusieurs dossiers (récursif), unité 15 min, NQ + MES
$PY tools/strategie/optim/run.py --data "/Users/jeremk/Jeu 15:10" --tf 15 --symboles NQ,MES
# historique long : fenêtres en jours de bourse
$PY tools/strategie/optim/run.py --data DOSSIER --tf 15 --symboles NQ,MES --apprentissage 120 --test 20
# JSON de l'API du terminal web (vrais prix) : passer le dossier qui contient api_vitrine_*.json
$PY tools/strategie/optim/run.py --data "$(ls -d tools/*_api)" --tf 15
# concordance avec engine.py (préréglages A, B, C, trade par trade)
$PY tools/strategie/optim/verif_engine.py --data "/Users/jeremk/Jeu 15:10" --tf 15
```

Options utiles : `--rapide` (démonstration), `--pine-seulement` (n'explore que des réglages existant dans
STRATEGIE_V1), `--n-aleatoire`, `--min-trades`, `--min-trades-appr`, `--ancre`, `--api oui|non`, `--sortie`.
Le rapport (`rapport.md`, `courbe_oos.png`, `trades_oos.csv`, `resultats.json`) va dans
`tools/strategie/optim/resultats/<unité>_<symboles>_<date>/`.

## Données attendues

- **Mode a** : exports TradingView du graphique en Heiken Ashi (avec CompletV3 et l'indicateur Volume).
  Les vrais prix sont reconstitués depuis le HA (`../recon.py`) : fiable en 15 min, pas en 1-3 min.
- **Mode b (recommandé)** : en plus, le même graphique exporté en **bougies standard** (même symbole,
  même unité, même période). Le type de chaque fichier est détecté tout seul ; les vrais prix deviennent
  exacts (appariement par horodatage, contrôlé par c_HA = (o+h+l+c)/4).
- Nom de fichier TradingView inchangé (« CME_MINI_NQZ2026, 15_xxxxx.csv ») : symbole et unité en sont tirés.
  Les doublons entre exports sont fusionnés (bougie la plus « chaude » gardée), la chauffe est coupée.
- Pour conclure il faut ~6-12 mois de 15 min MES + NQ, dont une période baissière (≥ 100 trades hors échantillon).

## Fichiers

| Fichier | Rôle |
|---|---|
| `config.toml` | espace de recherche (clés = noms des variables Pine), coûts, instruments, walk-forward, seuils |
| `donnees.py` | lecture des dossiers, détection HA / standard / API, fusion, séries (`../features.py`) |
| `univers.py` | toutes les séries en tableaux numpy : déclencheurs, filtres, sorties (cache des signaux) |
| `moteur.py` | exécution vectorisée (conventions de `../engine.py` et du Pine), sélection une position à la fois |
| `espace.py` | tirage, forme canonique, voisins (plateau), masques de filtres, bloc Pine |
| `optimiseur.py` | caches, score, choix de la zone stable, walk-forward |
| `robustesse.py` | bootstrap par jour, ruine, PSR/DSR, White / SPA |
| `rapport.py`, `run.py` | rapport et ligne de commande ; `verif_engine.py` : concordance avec `engine.py` |

Complément : `../maemfe/` étudie stops et sorties par excursions (MAE/MFE), déclencheur par déclencheur.
