#!/usr/bin/env python3
"""Etape 2 : TREND (a) et Dashator (b). On calcule, pour chaque unite et chaque
capture, une batterie de regles candidates, et on les confronte aux relevés de
l'original (15/10 NQ 15m, 14/10 NQ 5m, 12/10 MES 15m).
La barre 'en cours' = derniere barre <= heure de capture (valeur a l'export :
approximation, on signale les marges faibles)."""
import sys
from lib import *

L12 = '/Users/jeremk/Ephore/Lun12:10/'
SRC = {
    # capture: (symbole, cutoff, {tf: fichier})
    '15/10 11:53': ('NQ', '2026-10-15T11:53', None),
    '15/10 11:46': ('NQ', '2026-10-15T11:46', None),
    '14/10 11:55': ('NQ', '2026-10-14T11:55', None),
    '12/10 14:11': ('MES', '2026-10-12T14:11', {
        '1': None, '5': L12 + 'CME_MINI_MESZ2026, 5_2eb65.csv', '15': L12 + 'CME_MINI_MESZ2026, 15_7f431.csv',
        '60': L12 + 'CME_MINI_MESZ2026, 60_f32cb.csv', '240': L12 + 'CME_MINI_MESZ2026, 240_5b64a.csv',
        '1D': L12 + 'CME_MINI_MESZ2026, 1D_f6b91.csv'}),
}
# Releves de l'original : TREND (1m,5m,15m,1H,4H,1D) et Dashator ; None = inconnu
OBS_TREND = {
    '15/10 11:53': [None, 0, 0, 0, 0, 1],   # 12.png (1m cache) ; 11.png : 1m BULLISH
    '15/10 11:46': [1, 0, 0, 0, 0, 1],      # 9.png / 10.png
    '14/10 11:55': [0, 0, 0, 0, 0, 1],      # 7.png
    '12/10 14:11': [0, 0, 0, 1, 1, 1],      # ancienne session 7/8.png
}
OBS_DASH = {
    '15/10 11:53': ('12 Normal / 11 Groupe', [0, 0, 0, 0, 0, 0]),
    '15/10 11:46': ('10 Groupe (9 Normal = tout bleu)', [1, 1, 1, 0, 0, 0]),
    '14/10 11:55': ('7 Normal', [1, 1, 1, 1, 1, 1]),
    '12/10 14:11': ('8 Groupe (7 Normal = tout rouge)', [1, 1, 1, 1, 0, 1]),
}
TFS = ['1', '5', '15', '60', '240', '1D']

def bars(cap, tf):
    sym, cut, fmap = SRC[cap]
    if fmap is not None:
        fn = fmap.get(tf)
        if fn is None: return None
        b = load(fn)
    else:
        fs = files().get((sym, tf))
        if not fs: return None
        b = load(fs[0])
    day = cut[:10]
    if tf == '1D':
        b = [x for x in b if x['t'] <= day]
    else:
        b = [x for x in b if x['t'][:16] <= cut]
    if not b or (tf == '1' and not b[-1]['t'].startswith(day)): return None
    return b

def feats(b):
    o = [x['o'] for x in b]; h = [x['h'] for x in b]; l = [x['l'] for x in b]; c = [x['c'] for x in b]
    o4 = [(o[i] + h[i] + l[i] + c[i]) / 4 for i in range(len(c))]
    e50 = ema(c, 50); e20 = ema(c, 20); e200 = ema(c, 200); e9 = ema(c, 9); e21 = ema(c, 21)
    s50 = sma(c, 50); s20 = sma(c, 20)
    m, sg = macd(c, 12, 26, 9)
    r = rsi(c, 14)
    st = supertrend(h, l, c)
    vt = vidya_trend(c, h, l)
    h4, h32 = ema(o4, 4), ema(o4, 32)
    i = len(c) - 1; j = i - 1
    f = {
        'HAc>EMA50 (live)': c[i] > e50[i],
        'HAc>EMA50 [1] (cloturee)': c[j] > e50[j],
        'HAc>Moyenator1 CSV': (b[i]['m1'] is not None and c[i] > b[i]['m1']),
        'EMA20>EMA50': e20[i] > e50[i],
        'EMA9>EMA21': e9[i] > e21[i],
        'EMA50>EMA200': e50[i] > e200[i],
        'HAc>EMA200': c[i] > e200[i],
        'HAc>SMA50': s50[i] is not None and c[i] > s50[i],
        'HAc>SMA20': c[i] > s20[i],
        'EMA50 pente>0': e50[i] > e50[j],
        'MACD>sig': m[i] > sg[i],
        'MACD>0': m[i] > 0,
        'RSI>50': r[i] > 50,
        'SuperTrend': st[i] == 1,
        'VIDYA Midgar': vt[i],
        'Heishi EMA4>EMA32': h4[i] > h32[i],
        'Heishi [1]': h4[j] > h32[j],
        'HA bougie c>o (live)': c[i] > o[i],
        'HA bougie c>o [1]': c[j] > o[j],
        'HAc>HAc[1]': c[i] > c[j],
        'HAo>HAo[1]': o[i] > o[j],
    }
    marg = {'HAc>EMA50 (live)': (c[i] - e50[i]), 'HA bougie c>o (live)': c[i] - o[i]}
    return f, marg, b[i]['t']

if __name__ == '__main__':
    table = {}
    for cap in SRC:
        for k, tf in enumerate(TFS):
            b = bars(cap, tf)
            if b is None: continue
            f, marg, t = feats(b)
            table[(cap, tf)] = f
            print('%-12s %-4s live=%s  marge EMA50 %+.2f  marge c-o %+.2f' % (cap, tf, t, marg['HAc>EMA50 (live)'], marg['HA bougie c>o (live)']))
    names = list(next(iter(table.values())).keys())
    for title, OBS in (('TREND', OBS_TREND), ('DASHATOR (cases par unite)', OBS_DASH)):
        print('\n===== %s : accord par regle =====' % title)
        rows = []
        for nm in names:
            ok = tot = 0; det = []
            for cap in SRC:
                obs = OBS[cap] if title == 'TREND' else OBS[cap][1]
                s = ''
                for k, tf in enumerate(TFS):
                    if (cap, tf) not in table or obs[k] is None: s += '?'; continue
                    v = table[(cap, tf)][nm]; tot += 1
                    if int(v) == obs[k]: ok += 1; s += 'o'
                    else: s += 'X'
                det.append(s)
            rows.append((ok, tot, nm, ' '.join(det)))
        rows.sort(reverse=True)
        print('captures dans l ordre :', list(SRC), ' (o = accord, X = desaccord, ? = inconnu ; 1m,5m,15m,1H,4H,1D)')
        for ok, tot, nm, det in rows:
            print('  %2d/%2d  %-26s %s' % (ok, tot, nm, det))
