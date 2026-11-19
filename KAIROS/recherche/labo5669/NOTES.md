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
