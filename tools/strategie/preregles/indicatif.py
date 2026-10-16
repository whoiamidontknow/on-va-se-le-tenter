"""Résultat INDICATIF de chaque préréglage proposé, sur nos ~2 mois de 15 min (MESZ + NQZ, sept.-oct. 2026 ;
MES1! avr.-juil. pour C, sans volume donc sans climax ni Detector).

Simulation au plus près du Pine : une position à la fois, un signal pendant une position est ignoré,
3 trades maximum par jour, coûts 1 tick/côté + 1,25 $/contrat/côté, stop/objectif posés en distance depuis
le prix obtenu. Pas de break-even, pas de fin de séance (comme les préréglages).
Écart apparié à la référence (même signal, trade isolé) : IC 95 % par bootstrap des jours.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'maemfe'))
import numpy as np
import pandas as pd
import niveaux as nv, sl_tp as st, features, strat   # noqa: E402
from core import boot_moyenne                        # noqa: E402
from reaction import jour                            # noqa: E402

PIV = ('PY', 'PM', 'PW')
PRIO_DEF = ('PY', 'PM', 'DET', 'PW', 'MO', 'SES', 'RD')   # défaut du Pine : annuel > mensuel > detector > weekly > ...

PRESETS = {
    # nom : (déclencheur, fenêtre horaire Paris (début, fin) ou None, stop, objectif, sortie Heishinator)
    'A-ATR2-HEI':        ('A', None, ('atr', 2.0), None, True),
    'A-ATR1-HEI':        ('A', None, ('atr', 1.0), None, True),
    'A-ATR15-HEI':       ('A', None, ('atr', 1.5), None, True),
    'A-ATR25-HEI':       ('A', None, ('atr', 2.5), None, True),
    'A-ATR3-HEI':        ('A', None, ('atr', 3.0), None, True),
    'A-PTS-HEI':         ('A', None, ('pts', {'NQ': 80.0, 'MES': 13.0}), None, True),
    'A-JOUR-ATR2-HEI':   ('A', (480, 1380), ('atr', 2.0), None, True),
    'A-SLPIV-HEI':       ('A', None, ('niv', PIV, 1.0, 3.0, 0.1, 'HA', 2.0), None, True),
    'A-SLDEF-HEI':       ('A', None, ('niv', PRIO_DEF, 0.5, 3.5, 0.1, 'HA', 2.0), None, True),
    'A-SLDET-HEI':       ('A', None, ('niv', ('DET',) + PIV + ('MO', 'SES'), 1.0, 3.0, 0.1, 'HA', 2.0), None, True),
    'A-SLMOSES-HEI':     ('A', None, ('niv', ('MO', 'SES') + PIV, 1.0, 3.0, 0.1, 'HA', 2.0), None, True),
    'A-TPPIV-HEI':       ('A', None, ('atr', 2.0), ('niv', PIV, 1.5, 0.1, 'HA', 'aucun'), True),
    'A-TPPIVDET-HEI':    ('A', None, ('atr', 2.0), ('niv', PIV + ('DET',), 1.5, 0.1, 'HA', 'aucun'), True),
    'A-SLPIV-TPPIV-HEI': ('A', None, ('niv', PIV, 1.0, 3.0, 0.1, 'HA', 2.0), ('niv', PIV, 1.5, 0.1, 'HA', 'aucun'), True),
    'A-TPPIV2-SAUTE':    ('A', None, ('atr', 2.0), ('niv', PIV, 2.0, 0.1, 'HA', 'saute'), False),
    'A-TP3R':            ('A', None, ('atr', 2.0), ('R', 3.0), False),
    'C-ATR2-TPPIV-HEI':  ('C', None, ('atr', 2.0), ('niv', PIV, 1.5, 0.1, 'HA', 'aucun'), True),
    'C-ATR15-2R':        ('C', None, ('atr', 1.5), ('R', 2.0), False),
}


def signaux(S, trig, hr):
    strat.ensure_htf(S)
    nn = lambda i: not features.news(S['T'][i], S['tfm'])
    if trig == 'A':
        if not S['hasv']: return []
        E = [(i, d) for i, d in strat.e_clx(S) if d == 1 and strat.f_trend(S, i, d) and nn(i)]
    else:
        E = [(i, d) for i, d in strat.e_tl(S) if st.hors_londres(S, i) and nn(i)]
    if hr:
        def ok(i):
            d = S['T'][i].astimezone(features.PARIS); m = d.hour * 60 + d.minute
            return hr[0] <= m < hr[1]
        E = [(i, d) for i, d in E if ok(i)]
    return E


def plan(S, i, d, stop, tp, hei):
    a = S['ratr'][i]
    if not a: return None
    if stop[0] == 'atr': dist = stop[1] * a
    elif stop[0] == 'pts': dist = stop[1][S['inst']]
    else:
        _, pr, lo, hi, m, base, k = stop
        dist, _ = st.stop_niveau(S, i, d, pr, lo, hi, m, base)
        if dist is None: dist = k * a
    td = None
    if tp is not None:
        if tp[0] == 'R': td = tp[1] * dist
        else:
            _, grp, rmin, m, base, sans = tp
            td = st.cible_niveau(S, i, d, dist, grp, rmin, m, base, 'suivant')
            if td is None and sans == 'saute': return 'saute'
    return dist, td, hei


def simule(series, cfg, sequentiel=True):
    trig, hr, stop, tp, hei = cfg
    rows = []
    for S in series:
        libre = -1; parjour = {}
        for i, d in signaux(S, trig, hr):
            if sequentiel and i < libre: continue
            j = jour(S['T'][i])
            if sequentiel and parjour.get(j, 0) >= 3: continue
            p = plan(S, i, d, stop, tp, hei)
            if p is None or p == 'saute': continue
            dist, td, h = p
            tr = st._trade(S, i, d, dist, td, h)
            if tr is None: continue
            parjour[j] = parjour.get(j, 0) + 1
            libre = i + 1 + tr['nb']
            rows.append(dict(sym=S['sym'], inst=S['inst'], i=i, jour=j, R=tr['R'], usd=tr['usd'], why=tr['why']))
    return pd.DataFrame(rows)


def pf(x):
    g = x[x > 0].sum(); l_ = -x[x <= 0].sum()
    return g / l_ if l_ > 0 else np.inf


if __name__ == '__main__':
    series = nv.charger((15,))
    out = []
    iso = {k: simule(series, v, sequentiel=False) for k, v in PRESETS.items()}
    for k, v in PRESETS.items():
        q = simule(series, v)
        ref = 'A-ATR2-HEI' if v[0] == 'A' else 'C-ATR15-2R'
        rec = dict(preset=k, n=len(q))
        if len(q):
            rec.update(R=q['R'].mean(), pf=pf(q['usd'].values), stop=(q['why'] == 'stop').mean(),
                       usd_MES=q.loc[q['inst'] == 'MES', 'usd'].mean(), usd_NQ=q.loc[q['inst'] == 'NQ', 'usd'].mean(),
                       n_MES=int((q['inst'] == 'MES').sum()), n_NQ=int((q['inst'] == 'NQ').sum()),
                       R_MES=q.loc[q['inst'] == 'MES', 'R'].mean(), R_NQ=q.loc[q['inst'] == 'NQ', 'R'].mean())
        a = iso[k].set_index(['sym', 'i']); b = iso[ref].set_index(['sym', 'i'])
        j = a.join(b[['R']], rsuffix='_ref', how='inner')
        if len(j) >= 10 and k != ref:
            m, lo, hi = boot_moyenne((j['R'] - j['R_ref']).values, j['jour'].values, B=2000)
            rec.update(dR=m, dR_lo=lo, dR_hi=hi, n_app=len(j))
        out.append(rec)
    R = pd.DataFrame(out)
    pd.set_option('display.width', 250)
    print(R.to_string(index=False, float_format=lambda x: '%.3f' % x if abs(x) < 10 else '%.0f' % x))
    R.to_csv(os.path.join(HERE, 'indicatif.csv'), index=False)
