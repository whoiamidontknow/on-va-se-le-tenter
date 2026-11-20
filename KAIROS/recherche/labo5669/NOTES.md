# Labo 5669 — notes

## Améliorations du Relevé à demander à TALOS (via DAEMON, 19/11)
1. Écrire b1/b4 (et o1/o4, k1/k4) avec 5 décimales : 46 bougies par instrument ont 0.000 dans le
   commentaire, ce qui rend le signe (direction Dashator) inconnu et décale quelques trades en lecture b.
2. Ajouter l'ouverture de chaque bougie au parcours (o=16 valeurs) : les sorties « fin » se remplissent à
   l'ouverture de la bougie f+1, aujourd'hui estimée au milieu de la bougie quand elle est inconnue
   (34 à 37 trades sur 3 ans, écart cumulé de -465 à +136 $).

## Bougie non reproduite (étape 5)
Alerte MES du 02/11 00:45 (achat, sortie au temps) : aucune lecture ne la reproduit. Au recalcul, les
bougies de 00:15 et 00:30 ont com = 0 / fin = 1. Réouverture de séance au lendemain du passage des
États-Unis à l'heure d'hiver (01/11) : à vérifier dans le calcul de la fenêtre horaire en historique.

## Lecture k (dernière bougie terminée) non validée contre le testeur
Aucun export en préréglage 76 / 77 dans KAIROS-data. La lecture k applique à k1/k4 la règle qui
reproduit x2 à 99,97 % en lecture o ; un export Strat5669+ préréglage 77 (MNQ 15 min, 3 ans)
permettrait de la valider comme les lectures o et b.

## 20/11 — fantômes et volatilité (DAEMON, fantomes_vol.py)
Question de Jeremy : les trades fantômes sont-ils plus nombreux en période agitée (earnings, news) ?
2019-2024, scellé fermé. Fantôme = go56b sans go56 ; né après coup = go56 sans go56b.
- Taux de fantômes plat par quintile d'ATR relatif : MNQ 17-19 %, MES 16-21 %. 2020 (covid) = 2023.
- Nés après coup : plus fréquents au calme (Q1 : 50 % MNQ, 48 % MES).
- Résultat en lecture b par quintile : aucun quintile significativement positif (R entre -0,08 et +0,08, erreur ±0,045).
Conclusion : la volatilité ne prédit ni les fantômes ni le résultat. Le fantôme naît quand le Dashator 1 h / 4 h
est près de son seuil, pas quand le marché bouge fort. Limite : ATR, pas un calendrier d'annonces.
