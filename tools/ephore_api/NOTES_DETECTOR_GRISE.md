# Detector — le grisage des zones (12/10/2026)

Jeremy : « sur les dernières versions il rend grisés les detectors qui ne tiendront pas,
je ne sais vraiment pas comment il fait ».

## LA RÈGLE

```
pour chaque boîte Detector :
    grisée = (bas <= prix_courant <= haut)
```

**Une boîte est grisée exactement quand le prix est à l'intérieur.** Aucun paramètre libre.

## La preuve

Deux instantanés de l'API publique du terminal, distants de 10 jours. Le second a été
récupéré **après** avoir formulé l'hypothèse sur le premier : c'est donc une prédiction
vérifiée, pas un ajustement.

| copie | unité | prix réel | boîte contenant le prix | boîte grisée | |
|---|---|---:|---|---|---|
| 02/10 | 15m | 30741 | `det_bear_0` | `det_bear_0` | ✅ |
| 02/10 | 2m | 30743 | aucune | aucune | ✅ |
| 12/10 | 15m | 30817 | aucune | aucune | ✅ |
| 12/10 | 2m | 30840 | aucune | aucune | ✅ |

19 boîtes au total sur les deux copies, 1 grisée, et c'est exactement celle qui contient
le prix. Les 3 autres situations prédisent « aucune grisée » et c'est le cas.

Cohérent avec la documentation officielle (`EPHORE_METHODE.md`) :
> « une zone opposée **trop proche du prix** passe en gris (bruit visuel enlevé, info
> gardée). Basé sur la **DISTANCE**, pas la force. »

Et avec la FAQ du hub : « Mon Detector est passé en gris : je peux encore viser cette
zone ? » — l'information est conservée, c'est une atténuation visuelle.

## Ce qui est écarté

- **« Mitigée / consommée » : NON.** 8 boîtes sur 10 de la copie du 02/10 avaient été
  traversées par le prix depuis leur création, et une seule est grisée. Le grisage n'est
  donc pas la consommation de la zone.
- **La force : NON**, conforme à la doc. Volume à la création (grisée 5.85, non grisées de
  1.45 à 21.3), largeur (48.4 contre 5.7 à 88.4), nombre de touches (6, mais une non grisée
  en a 6 aussi) : aucune de ces mesures ne sépare.
- **« La boîte la plus proche » : NON.** Réfuté par le 2m, où la bear la plus proche n'est
  pas grisée.

## La réserve honnête

**Un seul cas positif.** On ne peut donc pas distinguer « le prix est dedans » (distance
nulle) d'un seuil « distance < k × ATR » pour un petit k. La doc dit « trop proche », ce qui
suggérerait k > 0. Bornes mesurées : la non grisée la plus proche était à **2.09 ATR** en 15m
et **2.85 ATR** en 2m, donc k se situe quelque part entre 0 et 2.

« Prix dedans » est la règle **minimale** qui explique les 19 observations, et c'est celle à
implémenter : elle n'a aucun paramètre à régler. Si un jour une boîte proche mais non
traversée apparaît grisée, il faudra passer à un seuil en ATR.

## Pour trancher

Plusieurs copies de l'API à des instants variés, idéalement avec des boîtes qui passent de
non grisé à grisé. Chaque copie coûte une requête. **Ne pas interroger en boucle.**
Scripts : `sim_detector_grise.py`, oracle dans `oracle_detector_grise.csv`,
copies `api_vitrine_instantane.json` (02/10) et `api_vitrine_20261012.json` (12/10).
