# Exporter le DATASET — procédure pour Jeremy

But : 6 fichiers CSV = MNQ1! et MES1!, chacun en 15 min, 5 min et 2 min, avec le plus d'historique possible.
Compte 5 minutes par fichier.

1. **Ajouter le script.** Dans TradingView, ouvre l'éditeur Pine, crée un nouvel indicateur, colle tout
   le contenu de `KAIROS/dataset/DATASET.pine`, enregistre, puis « Ajouter au graphique ».
   Il s'appelle **« Dataset KAIROS »**. Ne change aucun réglage.

2. **Préparer le graphique.** Type de bougies : **Heikin Ashi**. Retire **tous les autres indicateurs**
   (Complet V3, Volume, Stratégie…) : sinon leurs colonnes se mélangent à l'export.

3. **Choisir le symbole et l'unité.** Commence par **MNQ1!** en **15 min**.

4. **Charger tout l'historique.** Fais défiler le graphique vers la gauche (ou maintiens la flèche
   gauche du clavier) jusqu'à ce que plus aucune bougie ne se charge. Attends que le script ait fini
   de calculer (plus de petit rond qui tourne à côté de son nom).

5. **Exporter.** Menu du graphique (flèche à côté du nom de la disposition, en haut à droite) →
   **« Exporter les données du graphique… »** → Format de l'heure : **ISO** → **Exporter**.

6. **Ranger le fichier.** Dépose-le dans **`~/ERGON/KAIROS-data/`** (crée le dossier la
   première fois). **Ne le renomme pas** : le nom donné par TradingView (ex. `CME_MINI_MNQ1!, 15_ab12c.csv`)
   contient déjà le symbole et l'unité, le programme le lit tout seul.

7. **Recommencer** pour MNQ1! en **5** puis **2 min**, puis pour **MES1!** en 15, 5 et 2 min
   (étapes 3 à 6). À la fin : 6 fichiers dans le dossier.

8. **Prévenir l'équipe.** Si un export refuse de se faire, ou si le script affiche une erreur en rouge,
   envoie une capture : on corrige.

---
Contrôle côté équipe (pas besoin de le faire) :
`~/venv-quant/bin/python KAIROS/dataset/verifier.py ~/ERGON/KAIROS-data/*.csv`
