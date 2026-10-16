"""Synthèse lisible des études SL et TP : variantes de référence + variantes adaptatives « canoniques »
(fixées AVANT de regarder les résultats), puis contrôle du biais de sélection : la meilleure variante
adaptative choisie sur MES, que donne-t-elle sur NQ ? Combien de variantes ont un IC qui exclut 0 ?"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
import analyse as an

SL_CANON = ['ATR1.0', 'ATR1.5', 'ATR2.0', 'ATR2.5', 'ATR3.0', 'PTS0', 'PTS1', 'PTS2',
            'NIV|PROCHE sans ronds|1.0-3.0|m0.10|REEL|ATR2', 'NIV|PROCHE sans ronds|1.0-3.0|m0.10|HA|ATR2',
            'NIV|PIV>DET>MO>SES>RD|1.0-3.0|m0.10|HA|ATR2', 'NIV|PIV seuls|1.0-3.0|m0.10|HA|ATR2',
            'NIV|PIV seuls|1.0-3.0|m0.10|REEL|ATR2', 'NIV|DET>PIV>MO>SES|1.0-3.0|m0.10|REEL|ATR2',
            'NIV|MO+SES>PIV|1.0-3.0|m0.10|REEL|ATR2', 'NIV|PROCHE tous|0.5-2.0|m0.10|REEL|ATR2',
            'NIV|LOIN tous|1.0-3.0|m0.10|REEL|ATR2', 'NIV|PIV seuls|1.0-3.0|m0.10|HA|saute']
TP_CANON = ['Heishinator', 'Fixe 1R', 'Fixe 1.5R', 'Fixe 2R', 'Fixe 3R',
            'NIV|PIV|min1.0|suivant|HA|repli Heishi|seul', 'NIV|PIV|min1.5|suivant|HA|repli Heishi|seul',
            'NIV|PIV|min2.0|suivant|HA|repli Heishi|seul', 'NIV|PIV|min1.5|suivant|REEL|repli Heishi|seul',
            'NIV|PIV+DET|min1.5|suivant|HA|repli Heishi|seul', 'NIV|TOUS|min1.5|suivant|REEL|repli Heishi|seul',
            'NIV|PIV|min1.5|suivant|HA|repli Heishi|+Heishi', 'NIV|PIV|min1.5|suivant|HA|repli Fixe2R|seul',
            'NIV|PIV|min1.5|bloquant|HA|repli Heishi|seul', 'NIV|PIV+DET|min1.5|bloquant|HA|repli Heishi|seul',
            'NIV|PIV|min1.5|suivant|HA|repli saute|seul', 'NIV|DET|min1.5|suivant|HA|repli Heishi|seul']


def selection(r):
    a = r[r['var'].str.startswith('NIV') & r['dR_MES'].notna() & r['dR_NQ'].notna()]
    if len(a) == 0: return {}
    best = a.sort_values('dR_MES', ascending=False).iloc[0]
    sig_pos = int((a['dR_TOUT_lo'] > 0).sum()); sig_neg = int((a['dR_TOUT_hi'] < 0).sum())
    rho = float(np.corrcoef(a['dR_MES'], a['dR_NQ'])[0, 1]) if len(a) > 3 else np.nan
    return dict(nvar=len(a), ic_pos=sig_pos, ic_neg=sig_neg, moy_dR=float(a['dR_TOUT'].mean()),
                meilleure=best['var'], best_dR_MES=float(best['dR_MES']), best_dR_NQ=float(best['dR_NQ']),
                rang_NQ=int((a['dR_NQ'] > best['dR_NQ']).sum()) + 1, rho_MES_NQ=rho)


def montre(r, canon):
    c = ['var', 'n', 'saute', 'stop', 'R', 'usd', 'pf', 'dR_TOUT', 'dR_TOUT_lo', 'dR_TOUT_hi', 'dR_MES', 'dR_NQ',
         'dusd_TOUT', 'dusd_TOUT_lo', 'dusd_TOUT_hi', 'usd_MES', 'usd_NQ']
    x = r.set_index('var').reindex(canon).reset_index()
    x = x[[k for k in c if k in x.columns]]
    return x.to_string(index=False, float_format=lambda v: '%.3f' % v if abs(v) < 10 else '%.0f' % v)


if __name__ == '__main__':
    for nom, canon in (('sl', SL_CANON), ('tp', TP_CANON)):
        R = pd.read_pickle(os.path.join(HERE, 'cache_%s_resume.pkl' % nom))
        for k, r in R.items():
            print('=====', nom.upper(), k)
            print(montre(r, canon))
            print('  sélection :', selection(r))
            print()
