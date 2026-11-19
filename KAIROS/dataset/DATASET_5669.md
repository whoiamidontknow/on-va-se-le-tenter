# Dataset 5669 — colonnes et procédure d'export

Indicateur `KAIROS/dataset/DATASET_5669.pine` (19/11/2026). C'est une copie de `Strat5669_PLUS.pine` (commit 245a9cb)
jusqu'au calcul de `go_long` / `go_short`, sans la gestion des ordres ni l'affichage. Il n'envoie aucun ordre et ne
dessine rien. Ses réglages par défaut sont ceux de la stratégie : préréglage **56**, « Données multi-unités » =
**calcul d'origine**.

Chaque ligne du CSV correspond à une bougie du graphique, et chaque valeur est **connue à la clôture de cette
bougie**. Dans la stratégie, une entrée décidée sur la bougie n se remplit à l'ouverture de n+1 (1 tick de
glissement, commission 1,25 $ par contrat et par côté). Le stop et l'objectif sont posés à partir de `c` (vrai prix de
clôture de la bougie signal) : stop = c ∓ `sl_pts`, objectif = c ± `tp_pts`.

## Colonnes (60)

| Colonne | Sens |
|---|---|
| `time` | ajouté par TradingView : ouverture de la bougie (ISO) |
| `t_s`, `tc_s` | ouverture / clôture de la bougie, en secondes Unix |
| `o`, `h`, `l`, `c` | vrais prix OHLC (r_o … r_c, symbole sans Heikin Ashi) |
| `v` | volume |
| `hao`, `hah`, `hal`, `hac` | OHLC Heikin Ashi du graphique |
| `sF_L`, `sF_S` | Signator Fort long / short (0/1) |
| `sM_L`, `sM_S` | Signator Moyen long / short (0/1) |
| `hei_L`, `hei_S` | flip Heishinator haussier / baissier (0/1) |
| `tl_L`, `tl_S` | cassure de trendline (Breakator) (0/1) |
| `lvl_L`, `lvl_S` | cassure de niveau : sessions Asie / Londres / US, Monday high-low (0/1) |
| `clx_L`, `clx_S` | climax achat / vente (0/1) |
| `div_L`, `div_S` | divergence, seuil divX du préréglage (0/1) |
| `sig_L`, `sig_S` | déclencheur combiné du préréglage (OU des précédents activés) |
| `go_L`, `go_S` | entrée décidée par la stratégie, tous filtres compris, AVANT la règle « une seule position à la fois » |
| `atr` | ATR des vrais prix (r_atr, celle du stop) |
| `atr_ha` | ATR 14 Heikin Ashi (sg_atr, celle de e) |
| `sl_pts` | distance du stop en points = atrK × atr (atrK = 3 en 56) |
| `tp_pts` | distance de l'objectif en points = tpR × sl_pts (tpR = 0,6667 en 56) |
| `ema50` | EMA 50 du close HA (Moyenator 1) |
| `e` | (close HA − ema50) / atr_ha, non arrondi |
| `e_r` | e arrondi au dixième (jr_e) : c'est cette valeur que le filtre eMax compare (long ≤ 0,6 ; short ≥ −0,6) |
| `x2_L`, `x2_S` | filtre Dashator 1 h + 4 h + eMax tel que la stratégie l'applique (0/1) |
| `o1`, `o4` | Dashator 1 h / 4 h, corps HA / ATR, signé, **calcul d'origine** (valeur finale de la bougie en cours : fuite en historique) |
| `b1`, `b4` | idem, **bougie en cours comme en direct** (mode b) |
| `k1`, `k4` | idem, **dernière bougie terminée** (mode muClos des préréglages 76 / 77) |
| `gd_o`, `gd_b`, `gd_k` | GODLIKE dans chaque lecture : 1 long, −1 short, 0 non (seuil 0,025 sur 1 h ET 4 h) |
| `d1`, `d4` | direction Dashator 1 h / 4 h utilisée par la stratégie dans le réglage actif (1 / −1) |
| `cf_L`, `cf_S` | confiance 1 h × 4 h (%) d'un long / d'un short (préréglages 80-95) |
| `el1`, `el4` | minutes écoulées dans la bougie 1 h / 4 h à la clôture de la bougie |
| `fin` | bougie de sortie forcée (à plat 15:59 Chicago, ou fenêtre 00:20-22:15 Paris dépassée) : aucune entrée ; la position est fermée par `close_all` à l'ouverture de la bougie suivante |
| `pf` | à plat 15:59 Chicago seul (partie de `fin`) |
| `hr` | fenêtre horaire du préréglage respectée (toujours 1 en 56) |
| `bo` | hors blackout news (toujours 1 si le blackout est coupé) |
| `com` | filtres communs réunis (heures, blackout, trades par jour, ADX, pas `fin`, ATR connue) |
| `adx` | ADX 14 (Signator) |
| `vr` | ATR / sa moyenne 96 bougies (régime de volatilité) |

Ce que le moteur Python doit encore reproduire, et qui n'est pas dans le CSV :
- une seule position à la fois ;
- les sorties : stop, objectif, temps (tBar = 16 bougies en 56), `fin` ;
- le compteur de trades par jour (maxJour = 0 en 56, donc sans effet).

## Procédure pour Jeremy (MNQ1! et MES1!, 15 min)

1. Dans l'éditeur Pine, crée un nouvel indicateur, colle tout `KAIROS/dataset/DATASET_5669.pine`, enregistre, puis
   « Ajouter au graphique ». Il s'appelle **« Dataset 5669 »**. Ne change aucun réglage.
2. Graphique en **Heikin Ashi**, **MNQ1!**, **15 min**. Retire tous les autres indicateurs et stratégies, sinon leurs
   colonnes s'ajoutent à l'export.
3. Charge tout l'historique : fais défiler vers la gauche jusqu'à ce que plus rien ne se charge, puis attends que
   le script ait fini de calculer.
4. Menu de la disposition → **« Exporter les données du graphique… »** → heure **ISO** → Exporter.
5. Dépose le fichier dans **`~/ERGON/KAIROS-data/dataset5669/`** **sans le renommer**.
6. Recommence pour **MES1!** en 15 min.

### CSV brut pour départager stop et objectif

Même procédure, avec un graphique **en bougies normales (pas Heikin Ashi), sans aucun script**, en **5 min**, sur
MNQ1! puis MES1!. Dépose les fichiers dans le même dossier.

Le 5 min est l'unité la plus fine réaliste. Pour 3 ans, il faut environ 210 000 bougies en 5 min, contre plus d'un
million en 1 min, ce que le graphique ne charge pas. Avant d'exporter, regarde la date de la première bougie
chargée : si elle ne remonte pas jusqu'en octobre 2023, exporte quand même et signale la date.
