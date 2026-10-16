"""2. SL ADAPTATIF « niveau de protection » et 3. TP ADAPTATIF « prochain niveau », contre SL/TP fixes.

Mêmes entrées pour toutes les variantes (comparaison APPARIÉE, chaque signal = un trade isolé, 1 contrat).
Conventions de ../engine.py et ../stop_detector/sim.py : signal à la clôture de i, entrée à l'ouverture
vraie de i+1 + 1 tick ; stop rempli au stop (ou à l'ouverture qui l'a sauté) - 1 tick ; objectif rempli
s'il est dépassé d'un tick, - 1 tick ; stop et objectif dans la même barre -> stop ; sortie Heishinator :
changement de couleur à la clôture de j -> ouverture de j+1 - 1 tick ; 1,25 $/contrat/côté.
Valeur du point : MES 5 $, NQ 20 $.

SL « niveau de protection » (réglages du futur mode Pine) :
  candidats = niveaux connus à la clôture de i du côté protecteur (sous le close pour un long) ;
  distance = |close_i - niveau| + marge ; gardés si min_ATR <= distance <= max_ATR ;
  priorité = liste ordonnée de familles : on prend la 1re famille qui a un candidat, et dans cette famille
  le niveau le PLUS PROCHE (ou le plus lointain : priorité « LOIN ») ; sinon repli ATR x k (ou trade sauté).
  Familles : PY/PM/PW (pivots annuel/mensuel/weekly, base HA = affichée par CompletV3, ou REEL),
  DET (bas de zone Detector haussière pour un long / haut de zone baissière pour un short),
  MO (Monday H/L), SES (H/L des sessions Asie/Londres/US terminées), RD (ronds de 100).
TP « prochain niveau » : 1er niveau du jeu choisi au-delà de l'entrée tel que distance - marge >= ratio
  minimum x risque (mode « suivant ») ; ou mode « bloquant » : si le 1er niveau est trop proche, trade sauté.
  Sans niveau : repli (Heishinator ou objectif fixe) ou trade sauté.
"""
import os, sys, json, time, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
import niveaux as nv              # noqa: E402
import strat, features             # noqa: E402
from reaction import jour          # noqa: E402

SPEC = {'MES': (5.0, 0.25), 'NQ': (20.0, 0.25)}
COMM = 1.25
FIXPTS = {'MES': (5.0, 10.0, 15.0), 'NQ': (30.0, 60.0, 90.0)}


def hors_londres(S, i):
    d = S['T'][i].astimezone(features.PARIS); m = d.hour * 60 + d.minute
    return not (480 <= m < 870)


def declencheurs(S, pas_alea=8):
    strat.ensure_htf(S)
    r = np.random.default_rng(S['n'] * 31 + S['tfm'])
    nn = lambda i: not features.news(S['T'][i], S['tfm'])
    out = {'Aleatoire': [(i, int(r.choice((1, -1)))) for i in range(110, S['n'] - 2, pas_alea)],
           'Trendline': strat.e_tl(S),
           'Preset C': [(i, d) for i, d in strat.e_tl(S) if hors_londres(S, i) and nn(i)],
           'Heishinator': strat.e_heishi(S)}
    if S['hasv']:
        out['Climax BUY'] = [(i, d) for i, d in strat.e_clx(S) if d == 1]
        out['Preset A'] = [(i, d) for i, d in strat.e_clx(S) if d == 1 and strat.f_trend(S, i, d) and nn(i)]
        out['Fleche Fort'] = strat.e_sigF(S)
    return out


# ------------------------------------------------------------------ niveaux candidats
def groupe(fam):
    if fam.startswith('PY'): return 'PY'
    if fam.startswith('PM'): return 'PM'
    if fam.startswith('PW'): return 'PW'
    if fam in ('AS', 'LD', 'US'): return 'SES'
    return fam


def niveaux_cote(S, i, d, base):
    """Niveaux (groupe, prix) côté protecteur (d=+1 : sous le close) et côté objectif, séparés."""
    e = S['rc'][i]; prot = []; obj = []
    for fam, sub, L in S['LV'][i]:
        g = groupe(fam)
        if g in ('PY', 'PM', 'PW') and not fam.endswith(base): continue
        if g == 'RF': continue
        if fam == 'DB':
            if d == 1 and sub == 'btm' and L < e: prot.append(('DET', L))
            if d == -1 and L < e: obj.append(('DET', L))
            continue
        if fam == 'DS':
            if d == -1 and sub == 'top' and L > e: prot.append(('DET', L))
            if d == 1 and L > e: obj.append(('DET', L))
            continue
        if (L < e) == (d == 1): prot.append((g, L))
        else: obj.append((g, L))
    return prot, obj


def stop_niveau(S, i, d, prio, dmin, dmax, marge, base, loin=False):
    """Distance de stop (points) depuis le close de i, ou None. prio : tuple de groupes, ou ('PROCHE', ...)."""
    a = S['ratr'][i]; e = S['rc'][i]
    prot, _ = niveaux_cote(S, i, d, base)
    cands = []
    for g, L in prot:
        dist = abs(e - L) + marge * a
        if dmin * a <= dist <= dmax * a: cands.append((g, dist))
    if not cands: return None, None
    if prio[0] == 'PROCHE':
        ok = [c for c in cands if c[0] in prio[1:]]
        if not ok: return None, None
        c = (max if loin else min)(ok, key=lambda c: c[1]); return c[1], c[0]
    for g in prio:
        ok = [c for c in cands if c[0] == g]
        if ok:
            c = (max if loin else min)(ok, key=lambda c: c[1]); return c[1], c[0]
    return None, None


def cible_niveau(S, i, d, risk, groupes, rmin, marge, base, mode='suivant', rmax=12.0):
    """Distance d'objectif (points depuis le close de i) ou None ; 'BLOQUE' si mode bloquant et 1er niveau trop proche."""
    a = S['ratr'][i]; e = S['rc'][i]
    _, obj = niveaux_cote(S, i, d, base)
    ds = sorted(abs(L - e) - marge * a for g, L in obj if g in groupes)
    ds = [x for x in ds if x > 0]
    if not ds: return None
    if mode == 'bloquant':
        return ds[0] if ds[0] >= rmin * risk and ds[0] <= rmax * risk else 'BLOQUE'
    for x in ds:
        if x >= rmin * risk:
            return x if x <= rmax * risk else None
    return None


# ------------------------------------------------------------------ simulation
_MEMO = {}


def trade(S, i, d, dist, tdist=None, heishi=False):
    k = (id(S), i, d, round(dist, 6), None if tdist is None else round(tdist, 6), heishi)
    if k not in _MEMO: _MEMO[k] = _trade(S, i, d, dist, tdist, heishi)
    return _MEMO[k]


def _trade(S, i, d, dist, tdist=None, heishi=False):
    pv, tick = SPEC[S['inst']]
    n = S['n']
    if i + 1 >= n or S['brk'][i + 1] or not dist or dist <= 0: return None
    ro, rh, rl, rc, bull = S['ro'], S['rh'], S['rl'], S['rc'], S['bull']
    px = ro[i + 1] + d * tick
    st = px - d * dist
    tg = px + d * tdist if tdist else None
    j0 = i + 1; ex = None; why = None
    for j in range(j0, n):
        if (d == 1 and rl[j] <= st) or (d == -1 and rh[j] >= st):
            f = st if j == j0 else (min(ro[j], st) if d == 1 else max(ro[j], st))
            ex, why = f - d * tick, 'stop'; break
        if tg is not None and ((d == 1 and rh[j] >= tg + tick) or (d == -1 and rl[j] <= tg - tick)):
            ex, why = tg - d * tick, 'objectif'; break
        if heishi and bull[j] != (d == 1) and j + 1 < n:
            ex, why = ro[j + 1] - d * tick, 'signal'; break
    if ex is None:
        ex, why = rc[n - 1], 'fin'; j = n - 1
    pnl = d * (ex - px) - 2 * COMM / pv
    return dict(R=pnl / dist, usd=pnl * pv, why=why, nb=j - j0 + 1)


# ------------------------------------------------------------------ variantes
PRIOS = {
    'PIV>DET>MO>SES>RD': ('PY', 'PM', 'PW', 'DET', 'MO', 'SES', 'RD'),
    'PIV seuls': ('PY', 'PM', 'PW'),
    'DET>PIV>MO>SES': ('DET', 'PY', 'PM', 'PW', 'MO', 'SES'),
    'MO+SES>PIV': ('MO', 'SES', 'PY', 'PM', 'PW'),
    'PROCHE tous': ('PROCHE', 'PY', 'PM', 'PW', 'DET', 'MO', 'SES', 'RD'),
    'PROCHE sans ronds': ('PROCHE', 'PY', 'PM', 'PW', 'DET', 'MO', 'SES'),
    'LOIN tous': ('PROCHE', 'PY', 'PM', 'PW', 'DET', 'MO', 'SES', 'RD'),
}
FOURCH = ((0.5, 2.0), (1.0, 3.0), (0.5, 3.0), (1.5, 3.0))
MARGES = (0.1, 0.25)


def variantes_sl():
    V = {}
    for k in (1.0, 1.5, 2.0, 2.5, 3.0): V['ATR%.1f' % k] = ('atr', k)
    for j in range(3): V['PTS%d' % j] = ('pts', j)
    for (pn, pr), (a, b), m, base, fb in itertools.product(PRIOS.items(), FOURCH, MARGES, ('HA', 'REEL'), ('ATR2', 'saute')):
        V['NIV|%s|%.1f-%.1f|m%.2f|%s|%s' % (pn, a, b, m, base, fb)] = ('niv', pr, a, b, m, base, fb, pn.startswith('LOIN'))
    return V


def dist_sl(S, i, d, v):
    a = S['ratr'][i]
    if v[0] == 'atr': return v[1] * a, None
    if v[0] == 'pts': return FIXPTS[S['inst']][v[1]], None
    _, pr, lo, hi, m, base, fb, loin = v
    dd, g = stop_niveau(S, i, d, pr, lo, hi, m, base, loin)
    if dd is None:
        return (2.0 * a, 'repli') if fb == 'ATR2' else (None, 'saute')
    return dd, g


SORTIES_SL = {'Heishinator': dict(heishi=True), 'Objectif 2R': dict(R=2.0), 'Objectif 3 ATR': dict(atr=3.0)}


def etude_sl(series):
    V = variantes_sl(); rows = []
    for S in series:
        for trig, E in declencheurs(S).items():
            for i, d in E:
                a = S['ratr'][i]
                if not a or i + 1 >= S['n']: continue
                base = dict(trig=trig, inst=S['inst'], sym=S['sym'], i=i, d=d, jour=jour(S['T'][i]), t=S['T'][i].timestamp())
                for vn, v in V.items():
                    dist, g = dist_sl(S, i, d, v)
                    if dist is None:
                        rows.append(dict(base, var=vn, sortie='*', saute=True)); continue
                    for sn, so in SORTIES_SL.items():
                        td = so.get('R', 0) * dist if 'R' in so else (so['atr'] * a if 'atr' in so else None)
                        tr = trade(S, i, d, dist, td, so.get('heishi', False))
                        if tr is None: continue
                        rows.append(dict(base, var=vn, sortie=sn, saute=False, grp=g, dist_atr=dist / a,
                                         R=tr['R'], usd=tr['usd'], stop=tr['why'] == 'stop'))
    return pd.DataFrame(rows)


def variantes_tp():
    V = {'Heishinator': ('hei',), 'Fixe 1R': ('fix', 1.0), 'Fixe 1.5R': ('fix', 1.5), 'Fixe 2R': ('fix', 2.0), 'Fixe 3R': ('fix', 3.0)}
    SETS = {'PIV': ('PY', 'PM', 'PW'), 'PIV+DET': ('PY', 'PM', 'PW', 'DET'), 'TOUS': ('PY', 'PM', 'PW', 'DET', 'MO', 'SES', 'RD'),
            'DET': ('DET',), 'PIV+MO+SES': ('PY', 'PM', 'PW', 'MO', 'SES')}
    for (sn, st), rmin, mode, base, fb, hei in itertools.product(SETS.items(), (1.0, 1.5, 2.0), ('suivant', 'bloquant'),
                                                             ('HA', 'REEL'), ('Heishi', 'Fixe2R', 'saute'), (False, True)):
        V['NIV|%s|min%.1f|%s|%s|repli %s|%s' % (sn, rmin, mode, base, fb, '+Heishi' if hei else 'seul')] = ('niv', st, rmin, mode, base, fb, hei)
    return V


STOPS_TP = {'ATR2.0': ('atr', 2.0), 'NIV PROCHE 1.0-3.0 REEL': ('niv', PRIOS['PROCHE sans ronds'], 1.0, 3.0, 0.1, 'REEL', 'ATR2', False)}


def etude_tp(series):
    V = variantes_tp(); rows = []
    for S in series:
        for trig, E in declencheurs(S).items():
            for i, d in E:
                a = S['ratr'][i]
                if not a or i + 1 >= S['n']: continue
                base = dict(trig=trig, inst=S['inst'], sym=S['sym'], i=i, d=d, jour=jour(S['T'][i]), t=S['T'][i].timestamp())
                for stn, stv in STOPS_TP.items():
                    dist, _ = dist_sl(S, i, d, stv)
                    if dist is None: continue
                    for vn, v in V.items():
                        if v[0] == 'hei': td, hei = None, True
                        elif v[0] == 'fix': td, hei = v[1] * dist, False
                        else:
                            _, st, rmin, mode, b, fb, hei = v
                            td = cible_niveau(S, i, d, dist, st, rmin, 0.1, b, mode)
                            if td == 'BLOQUE' or (td is None and fb == 'saute'):
                                rows.append(dict(base, stop_var=stn, var=vn, saute=True)); continue
                            if td is None:
                                td, hei = (None, True) if fb == 'Heishi' else (2.0 * dist, hei)
                        tr = trade(S, i, d, dist, td, hei)
                        if tr is None: continue
                        rows.append(dict(base, stop_var=stn, var=vn, saute=False, R=tr['R'], usd=tr['usd'],
                                         stop=tr['why'] == 'stop', obj=tr['why'] == 'objectif',
                                         tR=(td / dist) if td else np.nan))
    return pd.DataFrame(rows)


if __name__ == '__main__':
    t0 = time.time()
    series = nv.charger((15,))
    print('séries', [(s['sym'], s['n']) for s in series], flush=True)
    which = sys.argv[1] if len(sys.argv) > 1 else 'sl,tp'
    if 'sl' in which:
        df = etude_sl(series); df.to_pickle(os.path.join(HERE, 'cache_sl.pkl'))
        print('SL : %d lignes %.0fs' % (len(df), time.time() - t0), flush=True)
    if 'tp' in which:
        df = etude_tp(series); df.to_pickle(os.path.join(HERE, 'cache_tp.pkl'))
        print('TP : %d lignes %.0fs' % (len(df), time.time() - t0), flush=True)
