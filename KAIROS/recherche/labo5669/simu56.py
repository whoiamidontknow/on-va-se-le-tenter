"""Simulateur du préréglage 56 de la Strat5669 sur la table du Relevé (KAIROS/dataset/releve.py).

Règles, d'après Strat5669.pine (sections 1 à 5 de la gestion des ordres) :
  - une position à la fois ; entrée sur go56 à la clôture de la bougie signal, remplie à l'ouverture
    de la bougie 1 (o1) avec 1 tick de glissement ; 2 contrats ; commission 1,25 $ / contrat / côté ;
  - stop et objectif recalés sur le PRIX OBTENU (pas sur c) : stop = entrée ∓ sl, objectif =
    entrée ± 0,6667 × sl. Sur la bougie 1, ils sont posés en ticks entiers (round(sl / tick)) ;
    dès la bougie 2, aux prix exacts, remplis au premier tick qui les atteint (vérifié sur l'export
    6ef10 : objectif 99 %, stop 100 %) ;
  - stop et objectif touchés dans la même bougie : stop d'abord (prudent), compté à part ;
  - sortie forcée `fin` sur la bougie f : remplie à l'ouverture de f + 1 (o17 si f = 16) ;
  - sortie au temps : clôture demandée à la bougie 16, remplie à l'ouverture de la bougie 17 (o17) ;
  - le stop (ordre stop) et les sorties au marché prennent 1 tick de glissement, pas l'objectif (limite) ;
  - après un stop ou un objectif sur la bougie k, une entrée est possible dès le signal de la bougie k ;
    après une sortie au marché remplie à l'ouverture d'une bougie, dès le signal de cette bougie
    (remplissage à la suivante).

Le parcours (h1..h16, l1..l16) doit être fiable (err16 ≈ 0) : exports Relevé a7d2173 et suivants.
"""
import numpy as np
import pandas as pd

TICK = 0.25
QTY = 2
COMM = 1.25
TPR = 0.6667
BARRE = pd.Timedelta(minutes=15)


def ouvertures(t):
    """Prix d'ouverture connus par horodatage (o1 à t1, o17 à t17), pour les sorties `fin`."""
    return pd.concat([t.set_index("t1").o1, t.set_index("t17").o17]).groupby(level=0).first()


def _cran(x):
    """Nombre de ticks jusqu'au premier tick qui atteint une distance exacte x (en ticks)."""
    return np.ceil(x - 1e-9)


def un_trade(r, d, opn, ambigu="stop"):
    """Un trade entré sur la ligne r (namedtuple de la table Relevé), sens d = 1 / -1.
    Retourne le dict du trade et l'heure à partir de laquelle un nouveau remplissage est permis."""
    fill = r.o1 + d * TICK
    dist = r.sl
    f = int(r.f) if r.f == r.f else 0
    dern = f if 0 < f < 16 else 16
    sortie = raison = k_sortie = None
    amb = approx = False
    for k in range(1, dern + 1):
        if k == 1:          # bougie de remplissage : distances en ticks entiers depuis le prix obtenu
            n_sl, n_tp = max(1, round(dist / TICK)), max(1, round(TPR * dist / TICK))
        else:               # ensuite prix exacts : premier tick qui les atteint
            n_sl, n_tp = _cran(dist / TICK), _cran(TPR * dist / TICK)
        stop, tp = fill - d * n_sl * TICK, fill + d * n_tp * TICK
        hi = r.o1 + getattr(r, f"h{k}") * TICK
        lo = r.o1 + getattr(r, f"l{k}") * TICK
        t_stop = lo <= stop if d > 0 else hi >= stop
        t_tp = hi >= tp if d > 0 else lo <= tp
        if t_stop and t_tp:
            amb = True
            t_stop, t_tp = ambigu == "stop", ambigu != "stop"
        if t_stop:
            sortie, raison, k_sortie = stop - d * TICK, "stop", k
            break
        if t_tp:
            sortie, raison, k_sortie = tp, "objectif", k
            break
    if sortie is not None:
        libre = r.t1 + k_sortie * BARRE          # signal de la bougie k -> remplissage en k + 1
    elif 0 < f < 16:
        tx = r.t1 + f * BARRE
        px = opn.get(tx)
        if px is None:                           # ouverture inconnue : milieu de la bougie f + 1
            px = r.o1 + (getattr(r, f"h{f + 1}") + getattr(r, f"l{f + 1}")) / 2 * TICK
            approx = True
        sortie, raison, k_sortie, libre = px - d * TICK, "fin", f, tx + pd.Timedelta(minutes=1)
    else:                                        # fin sur la bougie 16 : même remplissage, mais la Strat
        sortie, raison, k_sortie, libre = (r.o17 - d * TICK, "fin" if f == 16 else "temps", 16,   # teste fin avant le temps
                                           r.t17 + pd.Timedelta(minutes=1))
    return dict(t1=r.t1, sens="L" if d > 0 else "S", entree=fill, sortie=sortie, raison=raison, k=k_sortie,
                ambigu=amb, approx=approx), libre


def simuler(t, ambigu="stop", lecture="o", filtre=None):
    """lecture "o" = Dashator 1 h / 4 h d'origine (graphique), "b" = bougie en cours (direct).
    filtre : masque booléen optionnel sur t (ex. GODLIKE seulement), appliqué aux signaux."""
    vp = t.attrs["val_point"]
    opn = ouvertures(t)
    gl, gs = ("go56_L", "go56_S") if lecture == "o" else ("go56b_L", "go56b_S")
    m = t.parcours & ((t[gl] == 1) | (t[gs] == 1))
    if filtre is not None:
        m &= filtre
    t = t[m].sort_values("t1")
    trades, libre = [], pd.Timestamp.min
    for r in t.itertuples(index=False):
        if r.t1 < libre:
            continue
        d = 1 if getattr(r, gl) == 1 else -1
        tr, libre = un_trade(r, d, opn, ambigu)
        tr["pnl"] = (tr["sortie"] - tr["entree"]) * d * QTY * vp - 2 * QTY * COMM
        trades.append(tr)
    return pd.DataFrame(trades)
