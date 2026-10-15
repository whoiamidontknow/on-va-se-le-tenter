"""Robustesse : médiane, poids du meilleur trade, résultat sans le meilleur trade, durée moyenne."""
import engine as E, strat as T
from cands2 import SETS
from final import C
for name, (en, kw) in C.items():
    print('==', name[:60])
    for sn, L in SETS:
        tr = []
        for s in L: tr += E.run(s, T.ENTRIES[en](s), **kw)
        if not tr: continue
        R = sorted(t['R'] for t in tr)
        best = R[-1]; sans = (sum(R) - best) / max(len(R) - 1, 1); sans2 = (sum(R) - R[-1] - R[-2]) / max(len(R) - 2, 1)
        print('   %-11s n%3d méd %+.2f  meilleur %+.1fR  moy sans le meilleur %+.2f  sans les 2 meilleurs %+.2f  barres moy %.1f' % (
            sn, len(R), R[len(R) // 2], best, sans, sans2, sum(t['bars'] for t in tr) / len(tr)))
