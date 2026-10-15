#!/usr/bin/env python3
"""TREND 1m : l'original dit BULLISH a 11:45:30, 11:46 et ~11:53 (captures 9, 10, 11).
Detail barre par barre des candidats sur NQ 1m (et 3m pour comparaison)."""
from lib import *
for tf in ('1', '3'):
    b = get('NQ', tf); c = [x['c'] for x in b]; h = [x['h'] for x in b]; l = [x['l'] for x in b]; o = [x['o'] for x in b]
    e50 = ema(c, 50); vt = vidya_trend(c, h, l); st = supertrend(h, l, c); e20 = ema(c, 20)
    e200 = ema(c, 200)
    print('== NQ', tf, 'min')
    for i in range(len(b)):
        if '2026-10-15T11:3' <= b[i]['t'][:16] <= '2026-10-15T11:59':
            print(b[i]['t'][11:16], 'HAc %.2f EMA50 %.2f (CSV %.2f) marge %+.2f | VIDYA %d ST %d EMA20>50 %d c>EMA200 %d' % (c[i], e50[i], b[i]['m1'], c[i] - e50[i], vt[i], st[i] == 1, e20[i] > e50[i], c[i] > e200[i]))
