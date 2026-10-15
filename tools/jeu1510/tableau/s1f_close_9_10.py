#!/usr/bin/env python3
"""Cloture HA 15m (bougie 11:45) qui reproduit chaque capture du 15/10 :
9 (orig Normal), 10 (orig Groupe), 12 (orig Normal), 11 (orig Groupe), 13 (nous)."""
from lib import *
b = get('NQ', '15', 1); c0 = [x['c'] for x in b]
H, L = 29860.5, 29828.75
for name, (tR, tC) in [('9 orig', (45.64, -25.0)), ('10 orig grp', (45.89, -22.64)), ('12 orig', (45.40, -27.34)), ('11 orig grp', (45.30, -28.28)), ('13 nous', (45.27, -28.52))]:
    best = None
    for k in range(-800, 800):
        x = 29848.5625 + k * 0.015625; c = c0[:-1] + [x]
        r = rsi(c)[-1]; cc = cci(c, 30)[-1]; s = sma(c, 10)[-1]
        d = abs(r - tR) * 10 + abs(cc - tC)
        if best is None or d < best[0]: best = (d, x, r, cc, (x - s) / s * 100)
    print('%-12s HA close %.4f  RSI %.2f CCI %.2f YoYo %.3f  err %.3f  => O+C reel = %.2f' % (name, best[1], best[2], best[3], best[4], best[0], 4 * best[1] - H - L))
