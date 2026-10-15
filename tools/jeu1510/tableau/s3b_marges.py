#!/usr/bin/env python3
"""Marges close HA - EMA50 en 3 min autour des captures du 14/10 et du 15/10."""
from lib import *
b = get('NQ', '3'); c = [x['c'] for x in b]; e = ema(c, 50)
for i, x in enumerate(b):
    if '2026-10-14T11:3' <= x['t'][:16] <= '2026-10-14T12:03' or '2026-10-15T11:39' <= x['t'][:16]:
        print(x['t'][:16], '%+.2f' % (c[i] - e[i]))
