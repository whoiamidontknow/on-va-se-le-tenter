#!/usr/bin/env python3
"""Solveur : pour chaque (symbole, unite, barre) d'un jour donne, on remplace la
cloture HA de la barre (supposee en cours) et on cherche si UNE valeur reproduit
a la fois le RSI14 et le CCI30 de la capture (2 equations, 1 inconnue : test fort).
Usage : python3 s1d_solveur_live.py 2026-10-14 49.22 -31.79"""
import sys
from lib import *

day, tR, tC = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
out = []
for (sym, tf), fns in files().items():
    if tf in ('1D', '720', '240'):
        continue
    b = load(fns[0])
    c0 = [x['c'] for x in b]
    g = [0.0] + [max(c0[j] - c0[j - 1], 0) for j in range(1, len(c0))]
    ls = [0.0] + [max(c0[j - 1] - c0[j], 0) for j in range(1, len(c0))]
    ag = [None] + rma(g[1:], 14); al = [None] + rma(ls[1:], 14)
    tick = 0.25 if sym == 'NQ' else 0.0625
    for i in range(60, len(b)):
        if not b[i]['t'].startswith(day):
            continue
        best = None
        for k in range(-200, 201):
            x = c0[i] + k * tick * 0.5
            d1 = x - c0[i - 1]
            a_g = (ag[i - 1] * 13 + max(d1, 0)) / 14; a_l = (al[i - 1] * 13 + max(-d1, 0)) / 14
            r = 100.0 if a_l == 0 else 100 - 100 / (1 + a_g / a_l)
            w = c0[i - 29:i] + [x]; m = sum(w) / 30; md = sum(abs(y - m) for y in w) / 30
            cc = (x - m) / (0.015 * md)
            d = abs(r - tR) * 10 + abs(cc - tC)
            if best is None or d < best[0]:
                best = (d, x, r, cc)
        out.append((best[0], sym, tf, b[i]['t'], best[1], best[2], best[3], c0[i]))
out.sort()
for x in out[:8]:
    print('err %.3f  %s %s %s  close %.4f (CSV %.4f) -> RSI %.2f CCI %.2f' % (x[0], x[1], x[2], x[3], x[4], x[7], x[5], x[6]))
