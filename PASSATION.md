# PASSATION — reprendre le projet Ephore sur un nouveau compte

> Écrit le 2026-10-02 par la session sortante, pour la session entrante.
> Jeremy change de compte Claude. Ce fichier est le mode d'emploi de l'ENVIRONNEMENT
> et de la REPRISE. La substance du projet (ce qui est validé, les formules, les
> données) est dans **`MEMOIRE_PROJET.md`** — ce fichier ne la recopie pas.

## 0. Ordre de lecture, dans cet ordre exact

1. **`MEMOIRE_PROJET.md`** (206 lignes) — l'état du projet. Rien ne se comprend sans lui.
2. **Ce fichier, §1 à §4** — l'environnement à réparer avant de produire du code.
3. **`EPHORE_METHODE.md`** — la logique officielle tirée de la formation.
4. Au besoin : `TL_LAB_COMBOS.md` (protocole trendlines).
   **Ne pas lire `trendlinediag.md`** : document du 29/09 sur une approche **abandonnée** (voir §6).

La mémoire auto (`~/.claude/projects/-Users-jeremk-Ephore/memory/`) est sur le disque,
elle survit au changement de compte. Elle se charge seule.

## 1. À RÉPARER EN PREMIER : un vérificateur de syntaxe Pine dormant

Tout le projet répète « on ne peut pas compiler le Pine ici ». **C'est faux depuis avril.**
Deux serveurs MCP Pine sont déclarés dans `~/.claude/settings.json`, sous une clé
`mcpServers` qui **n'existe pas dans le schéma** de ce fichier : Claude Code l'ignore
silencieusement. `claude mcp list` ne montre que les connecteurs claude.ai.

État réel, testé par handshake JSON-RPC le 02/10 :

| Serveur | État | Ce qu'il apporte |
|---|---|---|
| `pinescript-mcp` (node) | **FONCTIONNE** (serveur `pinescript` v1.1.0) | 5 outils de doc Pine v6 : `pine_search`, `pine_reference`, `pine_guide`, `pine_examples`, `pine_categories` |
| `pinescript-syntax-checker` (python) | **CASSÉ** | expose `check_syntax(pine_code)` qui interroge l'**API officielle TradingView** et renvoie erreurs + ligne + colonne |

Le second est le plus précieux : il lèverait le verrou central du projet. Cause de la panne,
diagnostiquée : le module Python `mcp` exige **Python ≥ 3.10**, et la machine n'a que
**3.9.6** (système et `whisper-env`), sans `brew`, `uv` ni `pipx`. Le paquet existe sur
PyPI (`pinescript-syntax-checker` v0.1.0, `requires_python >= 3.10`).

### Procédure
```bash
# 1. retirer la clé morte de ~/.claude/settings.json  (clé "mcpServers" -> à supprimer,
#    garder model / effortLevel / modelSettings / tui). DEMANDER À JEREMY AVANT.

# 2. enregistrer le serveur qui marche, là où Claude Code le lit vraiment
claude mcp add --scope user --transport stdio pinescript-mcp -- \
  node /Users/jeremk/.nvm/versions/node/v20.20.2/lib/node_modules/pinescript-mcp-server/dist/index.js

# 3. réparer le checker : uv télécharge son propre Python, c'est la voie de son README
curl -LsSf https://astral.sh/uv/install.sh | sh
claude mcp add --scope user --transport stdio pinescript-syntax-checker -- \
  uvx pinescript-syntax-checker

# 4. vérifier
claude mcp list            # les 2 doivent apparaître connectés
```
Piège : les chemins `node` sont codés en dur sur `v20.20.2`. Ils casseront au passage à
Node 22 (voir §3). Préférer `node` via le PATH une fois Node 22 en place.

## 2. Plugins : rien n'est installé, et 8 agents maison dorment

`~/.claude/plugins/known_marketplaces.json` ne contient que `claude-plugins-official`.
Aucune clé `enabledPlugins` nulle part → **aucun plugin tiers actif**.

Mais le dépôt `on-va-se-le-tenter` **est lui-même** une copie du plugin `superpowers`
v5.0.4 (obra/superpowers) : `.claude-plugin/plugin.json`, `agents/` (9), `skills/` (14),
`commands/` (3), `hooks/`. Layout de plugin ⇒ **inerte** tant que le plugin n'est pas installé.
Et il n'existe **ni `~/.claude/agents/`, ni `.claude/agents/`** : zéro agent personnalisé chargé.

**Nuance vérifiée en git, à ne pas manquer :** un seul des 9 agents vient de superpowers.
Les 8 autres sont des ajouts de Jeremy. Installer superpowers depuis le marketplace ne les
restaurera donc **pas**.

| Agent | Origine | Utile ici ? |
|---|---|---|
| `code-reviewer` | superpowers (78440e1, 17/03, par Claude) | marginal (pas de tests locaux) |
| `debugger`, `tdd-developer`, `planner`, `parallel-dispatcher`, `branch-finisher` | Jeremy, 686b29b, 20/03 | génériques ; `parallel-dispatcher` seul a un intérêt réel |
| **`pine-logic-simulator`** | Jeremy, 6359cdd, 21/03 | **oui** — rejoue une règle barre par barre pour la confronter aux screens |
| **`visual-chart-decoder`** | Jeremy, 6359cdd, 21/03 | **oui** — extrait les règles depuis des captures TradingView |
| **`indicator-decoder-lead`** | Jeremy, 6359cdd, 21/03 | **oui** — synthétise les deux précédents en hypothèses classées |

Ces trois-là sont taillés exactement pour ce projet et n'ont jamais tourné.

### Procédure
```bash
# superpowers depuis le marketplace officiel (vérifié présent, sha 5bf4e78)
claude plugin install superpowers@claude-plugins-official

# PUIS rendre les 8 agents maison réellement chargeables (portée utilisateur)
mkdir -p ~/.claude/agents
cp /Users/jeremk/Ephore/on-va-se-le-tenter/agents/*.md ~/.claude/agents/

claude plugin list    # vérifier superpowers actif
# en session : /agents doit lister pine-logic-simulator, visual-chart-decoder, indicator-decoder-lead
```

## 3. Environnement machine (constaté le 02/10)

| Élément | Valeur | Remarque |
|---|---|---|
| Claude Code | 2.1.285 | |
| Node | **v20.20.2** | **Claude Code exige ≥ 22** → warning `EBADENGINE` à chaque install |
| npm | 11.12.1 | |
| Python | 3.9.6 (système + `whisper-env`) | trop vieux pour le SDK `mcp` (§1) |
| git | 2.50.1 | |
| whisper | `/Users/jeremk/whisper-env/bin/python` | `mlx_whisper` OK ; `ffmpeg` est **dans le venv**, pas dans le PATH |
| brew / uv / pipx | **absents** | |

Node 22 (à lancer par Jeremy, `nvm` est une fonction shell) :
```bash
nvm install 22 && nvm alias default 22 && npm install -g @anthropic-ai/claude-code@latest
```
Les globaux npm ne sont pas partagés entre versions de Node : il faut réinstaller.

## 4. Changement de compte : ce qui survit, ce qui ne survit pas

**Survit** (sur le disque, hors compte) : la mémoire auto (4 fichiers), `~/.claude/settings.json`
(`model: opus`, `effortLevel: high`, `tui: fullscreen`), `~/Ephore/.claude/settings.local.json`
(5 règles de permission), le dépôt git, la **clé SSH GitHub** (authentifiée comme `whoiamidontknow`),
toutes les données CSV, la formation, `whisper-env`.

**Ne survit pas** (lié au compte) : les connecteurs claude.ai (Docs, Drive, Gmail, Calendar)
→ à réauthentifier ; les artifacts ; l'historique des sessions (donc pas de `claude -c`
vers les anciennes conversations).

## 5. Règles de travail avec Jeremy — non négociables

- **Commit + push après chaque modification, sans redemander.** Jamais `.DS_Store`.
  Branche `claude/install-superpowers-plugin-1EQcd`, remote `git@github.com:whoiamidontknow/on-va-se-le-tenter.git`.
  Messages conventionnels (`feat(tableau):`, `fix(porsche):`), **sans accents dans le corps**.
- **`PORSCHEONARRIVE.pine` : ne jamais y intégrer un nouveau chantier sans son accord explicite.**
  Le 30/09 il a fait annuler l'intégration des tableaux (« pourquoi tu as changé porsche ») :
  commit `8cf984e` créait une V9, `df89e1d` l'a révoquée. Les tableaux vivent dans `TABLEAU.pine`.
- **Du `.pine`, pas du code dans des `.md`.** Il l'a demandé explicitement.
  Version + journal dans l'en-tête de chaque fichier actif, à incrémenter.
- **Répondre en français, simplement.**
- **Utiliser des agents en parallèle** pour les grosses recherches.
- **Vérifier sur données avant de lui envoyer du code.** Jamais d'intuition.
- **Toujours dire quand on n'a pas pu compiler**, et lui demander le message rouge de TradingView.
  (À réévaluer une fois §1 réparé.)

## 6. Pièges propres au dépôt

- **`trendline_sim.py` (racine) et `trendlinediag.md` appartiennent à l'approche trendlines V2
  ABANDONNÉE** (29/09). La règle retenue est celle d'Amphibiantrading, dans `TL_LAB.pine` et
  `PORSCHEONARRIVE.pine`, simulée par `tools/tl_lab_sim.py`. Ne pas repartir des deux premiers.
- **`tools/tl_rule_search.py` est définitivement cassé** : il importe `amph_sim`, qui n'a
  jamais été commité (vérifié sur tout l'historique).
- Libellés internes désalignés : `TABLEAU.pine` est en V8 mais sa section dit « V7 » ;
  `PORSCHEONARRIVE.pine` est en V8 avec une section « TABLEAU PRINCIPAL V6 ».
- Fichiers `.pine` abandonnés à ignorer : `TL_FIGEE`, `TL_PAIRES`, `TRENDLINES`, `SIGNATOR`,
  `REPLIQUE`, `ZORADIK`. Non classés et probablement morts : `BREAKOUT_DIAG`, `CLIMAX`,
  `DIRECTIONNOR`, `FIBONACCI_AUTO`, `HA_DIAGNOSTIC*`, `HEISHINATOR*`, `PIVATOR_WEEKLY`, `TL_DIAG*`.
- Pièges Pine v6 : voir `MEMOIRE_PROJET.md` §8. `pine_reference` (§1) permet maintenant de les
  vérifier au lieu de les deviner.

## 7. TRAVAIL PERDU — ne pas le rechercher

Les scratchpads `/private/tmp` cités par `MEMOIRE_PROJET.md` §6 et §10 sont **vides** : `/tmp`
est volatile. Sont perdus :
- `signator_v9/NOTES.md` — les **~25 variantes testées** pour les flèches en trop du Signator ;
- `signator_final/{final_v8.py, v7eval.py, grid_v8.py}`, `signator_fit/`, `sim_figee.py`.

**Ce qui est sauf** : la *règle* Signator V8 est entièrement encodée et commentée dans
`TABLEAU.pine` (lignes 290-351, tooltips compris). Elle est donc reconstructible.
**Ce qui est perdu** : les scripts, et la liste des pistes déjà écartées. Risque concret de
refaire 25 tests inutiles.

**Action recommandée en priorité 2** : recréer un simulateur Signator depuis `TABLEAU.pine` V8,
le commiter dans `tools/`, et **ne plus jamais laisser un script décisif dans le scratchpad**.

## 8. Première session : ordre d'attaque proposé

1. Lire `MEMOIRE_PROJET.md`.
2. Réparer les MCP (§1) — ça change la façon de travailler pour tout le reste.
3. Installer superpowers + copier les 8 agents maison (§2).
4. Recréer `tools/signator_sim.py` depuis `TABLEAU.pine` V8 (§7), vérifier qu'il retrouve
   112/113 et 65/65 sur `~/Ephore/Singal` et `~/Ephore/Filtres`, puis commit.
5. Demander à Jeremy ce qu'il veut attaquer : **TBT** (il manque 3-4 screens du tableau de
   l'original au moment où TBT change, + le CSV au même instant) ou les **tableaux manquants**
   (INDICATOR|SIGNAL, TIMEFRAME|TREND|STRENGTH, Dashator).
