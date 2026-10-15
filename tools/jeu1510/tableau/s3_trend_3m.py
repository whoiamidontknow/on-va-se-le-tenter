#!/usr/bin/env python3
"""TREND : hypothese H = (1) la 1re ligne TREND/STRENGTH est calculee en 3 min
(liste TIMEFRAME de l'ancienne version : 3,5,15,60,240,1D ; la colonne '1m' n'est que
le libelle du Dashator) ; (2) chaque unite lit la bougie CLOTUREE (close[1] > EMA50[1],
idiome request.security lookahead_on + [1]). Comparaison live vs cloturee."""
from s2_trend_dash import bars, SRC
from lib import *
import s2_trend_dash as S

S.SRC['15/10 11:55'] = ('NQ', '2026-10-15T11:55', None)
OBS = {  # TREND original, unites 3(ou 1),5,15,60,240,1D
    '15/10 11:55': [1, 0, 0, 0, 0, 1],   # 11.png (2 BULLISH -> 1re ligne + 1D) ; 12.png identique sauf 1re ligne cachee
    '15/10 11:46': [1, 0, 0, 0, 0, 1],   # 9.png / 10.png
    '14/10 11:55': [0, 0, 0, 0, 0, 1],   # 7.png
    '12/10 14:11': [0, 0, 0, 1, 1, 1],   # 7/8.png de la session du 12/10
}
for first in ('1', '3'):
    for mode in ('live', 'cloturee'):
        ok = tot = 0; det = []
        for cap, obs in OBS.items():
            s = ''
            for k, tf in enumerate([first, '5', '15', '60', '240', '1D']):
                b = bars(cap, tf)
                if b is None: s += '?'; continue
                c = [x['c'] for x in b]; e = ema(c, 50)
                i = len(c) - 1 if mode == 'live' else len(c) - 2
                v = int(c[i] > e[i]); tot += 1
                if v == obs[k]: ok += 1; s += 'o'
                else: s += 'X(%+.0f)' % (c[i] - e[i])
            det.append(cap + ':' + s)
        print('1re ligne=%sm  bougie %-8s  %2d/%2d   %s' % (first, mode, ok, tot, '  '.join(det)))
