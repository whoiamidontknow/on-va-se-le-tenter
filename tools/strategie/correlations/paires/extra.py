"""Compléments : (1) redondance Moyenator / TREND par unité ; (2) motif « bougie HA 1H clôturée contre la bande
Moyenator » (repéré positif dans les 4 jeux, donc choisi EN REGARDANT la validation : chiffres non OOS)."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import backtest as B, defs, engine as E
df = B.df
d = df[df.set.isin(defs.SETS_MAIN)]
for tf in (5, 15, 30):
    x = d[d.tf == tf]
    cols = [c for c in ('trend_15', 'trend_30', 'trend_60', 'trend_240', 'trend_D', 'heishi', 'feu') if x[c].notna().mean() > .5]
    print('unité', tf, 'Moyenator(=TREND même unité) vs', {c: round(x.moy_pos50.corr(x[c], method='spearman'), 2) for c in cols},
          'accord TREND1H/Moyenator %.0f%%' % (100 * (np.sign(x.moy_pos50) == np.sign(x.trend_60)).mean()))


def r6():
    s = np.nan_to_num(np.sign(B.state('dash_60')))
    return np.where((s != 0) & (B.lab('moy_band', s) == 'contre'), s, 0)


for xn, kw in B.EXITS.items():
    res = B.run(r6, kw)
    print('== R6 bougie HA 1H contre bande Moyenator |', xn)
    for k in defs.SETS_MAIN + defs.SETS_X:
        tr = res.get(k, [])
        if tr: print('   %-13s %s | ATR/trade %+.2f' % (k, E.fmt(E.stats(tr)), np.mean([t['atr_units'] for t in tr])))
