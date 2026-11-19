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

## Relevé 5669 (stratégie) — c'est lui qu'on exporte

`KAIROS/dataset/RELEVE_5669.pine` reprend le même code, en **stratégie**, pour exporter 3 ans par le testeur en
historique profond. L'export du graphique, lui, est limité aux bougies chargées.

Principe : un trade d'1 contrat est ouvert à **chaque** bougie où un déclencheur existe dans le sens choisi
(`sig_L` ou `sig_S`, avant tout filtre). L'ID est « E » + bar_index. Le trade n'a ni stop ni objectif, et il est
fermé exactement 16 bougies plus tard. Les sorties de nuit et de 15h59 ne s'appliquent pas : les indicateurs `fin` /
`pf` sont dans les commentaires. Les réglages sont : pyramiding 40, commission 0, glissement 0, marge 0.
Pour chaque instrument, il faut un export **Long** et un export **Short**, parce que la position est nette sur
TradingView et qu'un short fermerait les longs.

**Commentaire d'entrée** (colonne Signal de la ligne d'entrée). Toutes les valeurs sont **brutes** : > 0 = haussier,
quel que soit le sens du relevé, à la différence de R16 qui signait dans le sens du trade.

`d=FH|go=1|x2=1|c=21034.50|atr=31.25|sl=93.75|er=0.4|o1=0.120|o4=0.031|b1=0.080|b4=-0.010|k1=0.150|k4=0.200|gd=1,0,1|cf=62|el=45,165|f=00111|adx=27|vr=1.12`

| Clé | Sens |
|---|---|
| `d` | déclencheurs présents dans le sens du relevé : F Signator Fort, M Moyen, H Heishinator, T trendline, N niveau, C climax, D divergence |
| `go` | la stratégie 56 aurait décidé l'entrée (tous filtres, avant « une position à la fois ») |
| `x2` | filtre Dashator 1 h + 4 h + eMax respecté |
| `c` | vrai close de la bougie signal |
| `atr`, `sl` | ATR des vrais prix, distance du stop = atrK × atr |
| `er` | écart à l'EMA50 en ATR HA, arrondi au dixième (valeur comparée à eMax) |
| `o1 o4`, `b1 b4`, `k1 k4` | Dashator 1 h / 4 h, corps HA / ATR : origine (fuite), en cours (direct), dernière terminée |
| `gd` | GODLIKE origine, en cours, dernière terminée (1 / −1 / 0) |
| `cf` | confiance 1 h × 4 h dans le sens du relevé (%) |
| `el` | minutes écoulées dans la bougie 1 h, 4 h |
| `f` | 5 chiffres : fin, pf, hr, bo, com |
| `adx`, `vr` | ADX 14, ATR / moyenne 96 bougies |

**Commentaire de sortie** (colonne Signal de la ligne de sortie) : le parcours des bougies 1 à 16 après l'entrée.
L'entrée se remplit à l'ouverture de la bougie 1. Tout est en **ticks entiers**, signés par rapport à ce prix
d'ouverture (prix − ouverture, sans tenir compte du sens).

`h=4,10,…(16 valeurs)|l=-3,1,…(16)|c=12|f=0|n=16`

`h` et `l` sont le haut et le bas de chaque bougie, `c` la clôture de la bougie 16, `f` la première bougie (1-16) où
`fin` passe à 1 (0 = aucune), et `n` le nombre de bougies.

Le testeur remplit la sortie à l'**ouverture de la bougie 17** : son prix de sortie n'est donc pas `c`. Les ordres sont
remplis sur les vrais prix (fill_orders_on_standard_ohlc), même sur un graphique Heikin Ashi. En fin d'historique,
les derniers trades (16 au plus) restent ouverts et n'ont pas de commentaire de sortie : il faut les ignorer.

**À contrôler sur le premier export :**
- **La longueur des commentaires.** L'entrée fait environ 230 caractères, et la sortie de 200 à 400 selon l'amplitude. Les relevés
  R16 ne dépassaient pas 115, et je n'ai pas pu mesurer la limite de TradingView. Si une valeur manque à la fin
  (`vr=` en entrée, `n=` en sortie), c'est que le commentaire a été coupé : prévenir TALOS, qui compactera.
- **Le nombre de trades.** On attend environ 3 500 à 4 500 trades par sens sur 3 ans en 15 min. Les relevés
  R16 en ont passé 8 670.

## Procédure pour Jeremy : 4 exports

1. Dans l'éditeur Pine, crée une nouvelle stratégie, colle tout `KAIROS/dataset/RELEVE_5669.pine`, enregistre,
   puis « Ajouter au graphique ». Elle s'appelle **« Relevé 5669 »**. Ne change aucun réglage, sauf le sens.
2. Graphique **MNQ1!**, **15 min**, **Heikin Ashi**. Retire les autres stratégies.
3. Dans les réglages, groupe « RELEVÉ » : **Sens du relevé = Long**.
4. Testeur de stratégie : active l'**historique profond** depuis le **16/10/2023**, jusqu'à aujourd'hui.
5. Exporte la liste des trades (même bouton d'export que d'habitude, fichier .xlsx).
6. Remets **Sens du relevé = Short** et refais les étapes 4 et 5.
7. Refais tout pour **MES1!** : à la fin, il y a 4 fichiers.
8. Dépose-les dans **`~/ERGON/KAIROS-data/dataset5669/`** **sans les renommer**.

Le CSV brut en 5 min n'est plus nécessaire : le parcours des 16 bougies est dans la sortie.

## Ancienne procédure (indicateur, export du graphique) — limitée aux bougies chargées

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
