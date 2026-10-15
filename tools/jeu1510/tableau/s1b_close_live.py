#!/usr/bin/env python3
"""Etape 1b : NQ 15m, bougie 11:45 en cours. Quelle cloture HA de la bougie
live reproduit chaque capture ? (RSI14, CCI30 sur close HA, YoYo SMA10)"""
from lib import *

b = get('NQ', '15', 1)
c0 = [x['c'] for x in b]
print('derniere barre CSV a0b3c :', b[-1])
for name, (tr_, tc) in {'12 orig': (45.4, -27.34), '13 nous': (45.27, -28.52), '11 orig grp': (45.3, -28.28)}.items():
    best = None
    for k in range(-400, 400):
        x = 29848.5625 + k * 0.0625
        c = c0[:-1] + [x]
        r = rsi(c)[-1]; cc = cci(c, 30)[-1]; s = sma(c, 10)[-1]
        d = abs(r - tr_) * 10 + abs(cc - tc)
        if best is None or d < best[0]:
            best = (d, x, r, cc, (x - s) / s * 100)
    print('%-12s close HA %.4f -> RSI %.2f CCI %.2f YoYo %.3f%%' % (name, best[1], best[2], best[3], best[4]))
