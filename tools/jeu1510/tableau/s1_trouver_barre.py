#!/usr/bin/env python3
"""Etape 1 : retrouver symbole / unite / minute de la capture 12.png
(original) : RSI14 45.4, CCI30 -27.34, YoYo 0.03 %. Notre 13.png : RSI 45.27,
CCI -28.52 ; 11.png : RSI 45.3, CCI -28.28. On balaye toutes les barres du 15/10."""
from lib import *

TARGETS = {'12.png orig': (45.4, -27.34), '13.png nous': (45.27, -28.52), '11.png orig groupe': (45.3, -28.28)}
res = []
for (sym, tf), fns in files().items():
    for k, fn in enumerate(fns):
        b = load(fn)
        c = [x['c'] for x in b]; h = [x['h'] for x in b]; l = [x['l'] for x in b]
        r = rsi(c, 14); cc = cci(c, 30); s10 = sma(c, 10)
        for i in range(len(b)):
            if not b[i]['t'].startswith('2026-10-15') or r[i] is None or cc[i] is None:
                continue
            yo = (c[i] - s10[i]) / s10[i] * 100
            for name, (tr_, tc) in TARGETS.items():
                d = abs(r[i] - tr_) + abs(cc[i] - tc) / 5
                res.append((d, name, sym, tf, k, b[i]['t'], r[i], cc[i], yo))
res.sort()
for name in TARGETS:
    print('==', name)
    for x in [y for y in res if y[1] == name][:6]:
        print('  d=%.3f %s %s#%d %s RSI %.2f CCI %.2f YoYo %.3f%%' % (x[0], x[2], x[3], x[4], x[5], x[6], x[7], x[8]))
