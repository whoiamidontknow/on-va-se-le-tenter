"""Contrôles : AUC par pli des variables seules (sans apprentissage) et corrélation des issues MES/NQ simultanées."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import models as M
C = M.CSV
for side in ('L', 'S'):
    yk = 'y' + side; print('==', side)
    for f in ('heishi_bull', 'heishi_spread', 'moy_dist50', 'trend_htf1', 'trend_htf2', 'rsi', 'macd_hist_rel', 'adx', 'atr_rel', 'piv_dist_P'):
        row = []
        for a, b in M.folds():
            te = C[(C.t >= a) & (C.t < b) & C[yk].notna() & C[f].notna()]
            row.append(roc_auc_score(te[yk], te[f]) if te[f].nunique() > 1 else np.nan)
        te = C[(C.t >= M.folds()[0][0]) & C[yk].notna() & C[f].notna()]
        auc = roc_auc_score(te[yk], te[f]); nul = M.null_auc(te[yk].values, te[f].values, te.serie.values, 300)
        print('  %-14s plis %s  poolé %.3f p_hasard(bilatéral) %.3f' % (f, ' '.join('%.3f' % x for x in row), auc,
              (1 + (np.abs(nul - .5) >= abs(auc - .5)).sum()) / 301))
# issues simultanées MES vs NQ (même unité, même horodatage)
m = C[C.sym == 'MES'][['t', 'tfm', 'yL']].dropna(); n = C[C.sym == 'NQ'][['t', 'tfm', 'yL']].dropna()
j = m.merge(n, on=['t', 'tfm'], suffixes=('_mes', '_nq'))
print('issues long MES/NQ au même instant : n=%d, accord %.3f, corrélation %.3f' % (len(j), (j.yL_mes == j.yL_nq).mean(), j[['yL_mes', 'yL_nq']].corr().iloc[0, 1]))
