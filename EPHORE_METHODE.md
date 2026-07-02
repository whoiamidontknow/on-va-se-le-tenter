# EPHORE MARKET ULTIMATE — Logique officielle (extraite de la formation d'Elio)

Source : PDFs de la formation payante (formation principale 28p + Rangeator 4p), extraits le 2026-07-01
dans `formation_txt/`. Ceci est la logique décrite **par l'auteur lui-même**, pas une hypothèse.
But : réécrire PORSCHEONARRIVE.pine et DIRECTIONNOR.pine sur des bases exactes.

## LA HIÉRARCHIE — d'où vient le SENS (capital)

Le sens d'un trade vient de **3 choses, et seulement elles** :
1. **Moyenator** = position du prix vs la ligne de filtre (tendance de fond).
2. **Climator** = qui domine (majorité des tables + dernier climax).
3. **Signator** = déclenche l'entrée (flèche).

Tout le reste (Detector, Pivator, Rondator, Fibonator, Breakator, Rangeator) = **confluence / zones / cibles**, JAMAIS le sens.

Pile de confluence (ordre officiel, ex-Rangeator PDF) :
`Moyenator (tendance) → Rangeator (structure range/cassure) → Climator (biais) → Detector/Pivator/Rondator/Trendlines (zones-cibles) → Signator (entrée)`

**Règle d'or : pas de confluence (min 3), pas de trade.**

## MODULES

### Moyenator — la "ligne de filtre" (= le SENS de base)
- **Double ligne adaptative** (→ nos 2 Moyenator EMA 50/60 dans PORSCHE = cohérent).
- Filtre de tendance + support/résistance dynamique.
- **Prix au-dessus = haussier (on cherche à acheter). En dessous = baissier (on vend).**
- Règle N°1 : achat = signal déclenché par une **bougie entière, sans contact, AU-DESSUS** de la ligne noire. Vente = bougie entière en dessous. Sinon on ignore.

### Heishinator — les bougies (VALIDÉ)
- Formule maison, bleu = haussier / rouge = baissier. (Notre règle SHA_close alpha 0.42/0.44 vs EMA33.)
- Le "signal" (flèche) se valide sur bougie Heishinator.

### Detector — zones institutionnelles = CIBLES (pas le sens)
- **Bleu = zone de demande** (cible côté long). **Rose/rouge = zone d'offre** (cible côté short).
- Sert de : objectif TP (prochaine zone opposée) + confluence d'entrée.
- Principe clé : **"d'où vient le prix"**. Sorti d'une zone forte + confluence → carburant pour traverser la 1ʳᵉ zone opposée et viser la 2ᵉ.
- **Zones atténuées (nouveauté)** : une zone opposée trop proche du prix passe en **gris** (bruit visuel enlevé, info gardée). Basé sur la DISTANCE, pas la force. Grisé par défaut, "masqué" en option.

### Climator — biais / mood (feu vert / rouge)
- Tables **bleu (acheteurs) / rouge (vendeurs) / orange (indécision)**. Règle : **majorité claire sinon on ne trade pas.**
- **Signaux climax** : triangle ↑ en bas = climax acheteur (bleu normal / **jaune** fort) ; triangle ↓ en haut = climax vendeur (rouge normal / **violet** fort). **Le dernier climax = biais directionnel, on ne trade jamais contre.**
- **Table TIMEFRAME / TREND / STRENGTH** (⚠ corrige notre implémentation) :
  - **TREND** = direction (bleu haussier / rouge baissier).
  - **STRENGTH** = thermomètre de la **pression ACHETEUSE** 0–100 %, PAS une direction : rouge = faible, orange = moyen, bleu = fort. Une grosse baisse fait CHUTER la jauge (peu d'acheteurs). TREND rouge + STRENGTH 100 % bleu = jambe baissière qui s'essouffle → rebond probable. **Donc strength ≠ % de confirmations alignées (notre formule actuelle est fausse).**

### Signator — flèches d'entrée
- Flèche achat/vente. Seule, ne suffit jamais : valider par Moyenator + Climator (dernier climax même sens) + confluences.

### Pivator — niveaux pro
- **Mensuel = NOIR, Hebdo (Weekly) = ORANGE, Annuel (Yearly) = ROUGE.** Hiérarchie **Y > M > W**. (PORSCHE : Set1 Annuel rouge + Set2 Mensuel noir = OK ; PIVATOR_WEEKLY doit être orange.)

### Breakator — cassure de trendline (triangle vert)
- Trendlines auto. **Focus sur trendlines baissières** (descendantes, au-dessus du prix) pour breakout haussier.
- Validation cassure : (1) clôture franche bougie Heishinator au-delà, (2) alignement Moyenator, (3) signal Signator dans le sens, (4) confluence Detector/Pivator/rond, (5) pas pendant news 3★. (Cohérent avec notre TRENDLINES.)

### Rondator — chiffres ronds (Nasdaq surtout)
### Fibonator — fib auto, NE donne JAMAIS le sens, zone 0.75 = confluence/TP. (Cohérent avec FIBONACCI_AUTO.)

### Rangeator — structure range/cassure (≠ Detector, mêmes rectangles !)
- Boîte autour d'une consolidation. **Gris = range/équilibre. Bleu = cassure haussière alignée Moyenator. Rouge = cassure baissière alignée.** La couleur suit le Moyenator, pas la boîte.
- Escalier de boîtes d'une couleur = continuation. Grosse boîte couleur opposée à l'extrême = retournement précoce. Amas gris = range plat (couleur = bruit).
- Détection sur **bougie fermée** (retard assumé, pas de repaint).

## RÈGLES OPÉRATIONNELLES
- **Stop** : sous la flèche pour un long, au-dessus pour un short (zones, pas au pip).
- **TP** : prochaine zone opposée Detector / Pivator / chiffre rond (marge de sécurité avant).
- **News 3★ US** (investing.com) : pas de trade 5 min avant→après.
- Marché intéressant ~30 % du temps ; 70 % = range = ne rien faire.
- Validation scalping = graph 2 min (entrées) + 15 min (tendance + gros objectifs Detector).

## IMPLICATIONS POUR NOS FICHIERS
- **DIRECTIONNOR** : le sens NON pas depuis la proximité des order-blocks (= Detector = cibles), mais **Moyenator (prix vs ligne) + Climator (majorité + dernier climax)**. RANGE = Climator indécis/mélangé OU boîte Rangeator grise. → refonte du moteur de sens.
- **PORSCHEONARRIVE** : corriger la colonne STRENGTH (pression acheteuse 0-100, pas % d'alignement) ; Pivator Weekly orange ; le Detector = cibles avec zones atténuées à ajouter ; ajouter un vrai module Rangeator (boîtes gris/bleu/rouge).

## RÉGLAGES CLIMATOR LITE (relevés du panneau v30, 2026-07-01)
- Cœur : période lissage **14** ; santé du mouvement : période **5**, sensibilité divergence **0.3** ; seuils pression **Forte 70 / Faible 30**.
- Climax : mode **Multi-niveaux** ; seuil mode Simple 55 ; niveau min à afficher **Standard** ; paliers **Faible 40 / Standard 55 / Fort 70 / Premium 85**.
- Confirmation : **valider à la clôture** (on) ; filtre santé « pas de filtre » ; **Preset EMU = Fort+Premium seulement** (on) → n'affiche que les climax ≥ Fort ; fenêtre confirmation **3** barres ; max labels 200.
- Couleurs BUY : Faible blanc, Standard cyan clair #7FC7D9, Fort indigo #5B5BF5, Premium jaune #F5E24E. SELL : Faible blanc, Standard rose clair #E8C6DE, Fort rouge #D65B50, Premium jaune #F5E24E.
- Couleurs Climator : Bullish #5B5BF5, Bearish #E05650, Neutre gris, Prudence ambre #F0B429. Thème dashboard : fond #15162D, accent header #5B5BD6.
- Biais (tableau, off par défaut) : 20 derniers signaux, source Fort+Premium, zone neutre ±10, Top Left.
- **Climax affiché** : ▲ en bas = acheteur, ▼ en haut = vendeur. Le calcul de « pression » est propriétaire (caché) → répliqué par proxy dans `CLIMAX.pine`, à calibrer.
- Le module standalone existe : `CLIMAX.pine` (indicateur "Ephore Climax (Replique)").
