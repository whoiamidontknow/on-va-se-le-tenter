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

## 24/11 — range contre tendance (DAEMON, range_tendance.py)
Question de Jeremy (posée pour le 2 min ; faite en 15 min faute de bougies 2 min). 56 lu sur bougies 1 h / 4 h
terminées (go56k), 2019-2024, trades indépendants. Régimes : Directionnor graphique / 1 h / 4 h (avec, contre, range)
et ADX 15 min (<20, 20-25, >25). 12 découpes × 2 instruments × 2 périodes.
- Aucun régime positif et significatif sur les deux instruments et les deux périodes. Meilleure case : ADX 20-25,
  R positif dans les 4 cases (+0,07 / +0,07 MNQ, +0,13 / +0,01 MES) mais erreur ±0,08-0,13, P&L négatif sur 2 cases sur 4.
- MES : ADX > 25 nettement perdant en 2019-22 (−0,30 ± 0,13), pas en 2023-24.
- Fantômes : 16-20 % partout ; seule exception MES contre la tendance 4 h, 24 %.
Conclusion : range ou tendance ne sépare pas les bons trades du 56 sur 15 min. Non inscrit comme candidat.

## 25/11 — score de fiabilité de la couleur 1 h / 4 h (idée de Jeremy, score_fiabilite.py)
p_tf = P(couleur finale = couleur en cours | |corps| en quintiles, part écoulée en quarts), table 2019-22 ; score = p1 × p4.
- La table confirme l'intuition : 1 h quasi sûre dès |corps| > 0,4 ; 4 h fragile (petit corps : 58 % en début de bougie,
  78 % même en fin de bougie).
- Sur les trades pris en direct (go56b), fantômes par quart de score, contrôle 2023-24 : MNQ 39 % → 18 %, MES 41 % → 22 %
  (même ordre en construction). Le score divise les fantômes par deux, ne les supprime pas.
- Résultat : MES moitié haute positive en contrôle (+2 549 $, Q3 R +0,10 ± 0,07), MNQ moitié haute négative (−2 047 $).
  Aucun avantage établi ; à ne pas présenter comme un filtre gagnant.
