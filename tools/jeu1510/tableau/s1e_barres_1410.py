#!/usr/bin/env python3
"""14/10 : RSI/CCI/YoYo des barres NQ 5m 11:30-12:00 en faisant varier la cloture live."""
from lib import *
b = get('NQ', '5'); c0 = [x['c'] for x in b]
for i, x in enumerate(b):
    if '2026-10-14T11:3' <= x['t'] <= '2026-10-14T12:00':
        best = {}
        for k in range(-200, 201):
            y = c0[i] + k * 0.125; c = c0[:i] + [y]
            r = rsi(c)[-1]; cc = cci(c, 30)[-1]; s = sma(c, 10)[-1]
            for nm, (tR, tC) in {'7orig': (49.22, -31.79), '6nous': (48.97, -33.84)}.items():
                d = abs(r - tR) * 10 + abs(cc - tC)
                if nm not in best or d < best[nm][0]: best[nm] = (d, y, r, cc, (y - s) / s * 100)
        print(x['t'], 'CSV', c0[i], {k: tuple(round(v, 3) for v in t) for k, t in best.items()})
