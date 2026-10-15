"""Référence sans signal pour juger R2 : entrée longue toutes les 4 barres si TREND HTF haussier,
même entrée (limite au milieu de la bougie, 4 barres) et même sortie (stop 1.5 ATR, obj 2R).
Et R2 avec détection prudente des remplissages limites (plus haut bas plausible)."""
import numpy as np, conf_common as C, strat as T
from conf_regles import JEUX, line, run_rule
L = C.L if hasattr(C, 'L') else C.load()
for jeu in JEUX:
    tr = []; tp = []; tri = []
    for S in L:
        sg = [(i, 1) for i in range(101, S['n'], 4) if JEUX[jeu](S, i) and T.f_trend(S, i, 1)]
        tr += C.sim(S, C.fills_limit(S, sg, C.lv_mid_bar, 4), stop_k=1.5, target=2)
        tri += C.sim(S, C.fills_immediate(S, sg), stop_k=1.5, target=2)
        cs = [(i, d) for i, d in C.apply_filter(S, C.trig(S, 'clxL'), T.f_trend) if JEUX[jeu](S, i)]
        tp += C.sim(S, C.fills_limit(S, cs, C.lv_mid_bar, 4, prudent=True), stop_k=1.5, target=2, prudent=True)
    print('%-16s REF long TREND limite-milieu %s\n%-16s REF long TREND immédiat     %s\n%-16s R2 remplissage prudent     %s' % (jeu, line(tr), '', line(tri), '', line(tp)))
