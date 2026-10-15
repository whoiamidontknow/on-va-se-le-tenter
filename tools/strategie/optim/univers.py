"""Univers : toutes les séries mises bout à bout en tableaux numpy (une ligne = une barre), avec
  - les vrais prix (exécution) et l'ATR14 des vrais prix ;
  - les DÉCLENCHEURS (sens +1/-1/0 connu à la clôture de la barre), calculés sur HA comme CompletV3 ;
  - les FILTRES et les SIGNAUX DE SORTIE ;
  - l'horodatage (Paris, New York) et la journée de bourse (clé du walk-forward et du bootstrap).
Tout est calculé UNE fois (cache des signaux) ; l'optimiseur ne fait ensuite que des masques.
"""
import datetime
import numpy as np
import features as F0
import strat as ST

NY, PARIS = F0.NY, F0.PARIS

DECLENCHEURS = ['fleche_fort', 'fleche_fort_moyen', 'heishi', 'trendline', 'niveau', 'climax', 'rebond_detector']


def _arr(x, dt=float):
    return np.array([np.nan if v is None else v for v in x], dt) if dt is float else np.asarray(x, dt)


def _sma(x, p):
    out = np.full(len(x), np.nan)
    c = np.nancumsum(np.where(np.isnan(x), 0, x))
    for i in range(p - 1, len(x)):
        w = x[i - p + 1:i + 1]
        if not np.isnan(w).any():
            out[i] = w.mean()
    return out


def _from_events(ev, n):
    a = np.zeros(n, np.int8)
    for i, d in ev:
        if a[i] == 0:
            a[i] = d
    return a


def _det_dist(S, i, longside):
    """Distance (en ATR HA) à la zone Detector opposée la plus proche, au sens de f_det_bloque (Pine)."""
    c = S['c'][i]; a = S['atr'][i]
    if not a:
        return np.inf
    zones = S['Zs'][i] if longside else S['Zb'][i]
    best = np.inf
    for t, b in zones:
        if longside and t >= c:
            best = min(best, max(b - c, 0.0) / a)
        if not longside and b <= c:
            best = min(best, max(c - t, 0.0) / a)
    return best


def serie_tableaux(S, htf_list, specs):
    n = S['n']; tfm = S['tfm']
    T = S['T']
    R = {}
    R['t'] = np.array([t.timestamp() for t in T])
    tp = [t.astimezone(PARIS) for t in T]
    tn = [t.astimezone(NY) for t in T]
    R['paris_min'] = np.array([t.hour * 60 + t.minute for t in tp], np.int16)
    tc = [(t + datetime.timedelta(minutes=tfm)).astimezone(PARIS) for t in T]
    R['paris_min_close'] = np.array([t.hour * 60 + t.minute for t in tc], np.int16)
    R['paris_date'] = np.array([t.year * 10000 + t.month * 100 + t.day for t in tp], np.int32)
    jd = [(t + datetime.timedelta(hours=6)).date() for t in tn]       # journée de bourse (18:00 NY -> 18:00 NY)
    R['jour'] = np.array([d.toordinal() for d in jd], np.int32)
    R['news'] = np.array([F0.news(t, tfm) for t in T], bool)
    for k in ('ro', 'rh', 'rl', 'rc', 'ratr', 'c', 'atr', 'adx', 'e50'):
        R[k] = _arr(S[k])
    R['brk'] = np.array(S['brk'], bool)
    bull = np.array(S['bull'], bool)
    R['bull'] = np.where(bull, 1, -1).astype(np.int8)
    run = np.array(S['run'])
    flip = np.where((run == 1) & (np.arange(n) > 0), R['bull'], 0).astype(np.int8)
    R['flip'] = flip
    sigF = np.array([x[1] if x and x[0] == 'F' else 0 for x in S['sig']], np.int8)
    sigM = np.array([x[1] if x and x[0] == 'M' else 0 for x in S['sig']], np.int8)
    R['fleche'] = np.where(sigF != 0, sigF, sigM).astype(np.int8)          # sortie « flèche opposée » (Fort ou Moyen)
    # ---- déclencheurs
    E = {}
    E['fleche_fort'] = sigF
    E['fleche_fort_moyen'] = R['fleche']
    E['heishi'] = flip
    E['trendline'] = np.where(np.array(S['rB']), 1, np.where(np.array(S['sB']), -1, 0)).astype(np.int8)
    ev = dict(ST.e_sess(S))
    for i, d in ST.e_mhl(S):
        ev.setdefault(i, d)
    E['niveau'] = _from_events(ev.items(), n)
    E['climax'] = np.array(S['clx'], np.int8) if S['hasv'] else np.zeros(n, np.int8)
    E['rebond_detector'] = _from_events(ST.e_det_rebond(S), n) if S['hasv'] else np.zeros(n, np.int8)
    for k, v in E.items():
        R['E_' + k] = v
    # ---- filtres
    R['ema_side'] = np.where(R['c'] > R['e50'], 1, -1).astype(np.int8)
    R['atr_rel'] = R['atr'] / _sma(R['atr'], 100)
    for m in htf_list:
        if m <= tfm or n / (m / tfm) <= 60:
            R['trend_%d' % m] = np.zeros(n, np.int8)
            continue
        f = F0.resample_real(S, m)
        R['trend_%d' % m] = np.array([0 if x is None else (1 if x['trend'] else -1) for x in f], np.int8)
    if S['hasv']:
        R['detL'] = np.array([_det_dist(S, i, True) for i in range(n)])
        R['detS'] = np.array([_det_dist(S, i, False) for i in range(n)])
    else:
        R['detL'] = np.full(n, np.inf); R['detS'] = np.full(n, np.inf)
    last = 0; lb = -10 ** 9; cl = np.zeros(n, np.int8); ca = np.zeros(n, np.int32)
    for i in range(n):
        if S['clx'][i]:
            last = S['clx'][i]; lb = i
        cl[i] = last; ca[i] = i - lb if last else 10 ** 6
    R['clx_last'] = cl; R['clx_age'] = ca
    ST.ensure_feu(S)
    R['feu'] = _arr(S['feu'])
    # ---- instrument
    pv, tick = specs
    R['pv'] = np.full(n, pv); R['tick'] = np.full(n, tick)
    return R


class Univers:
    def __init__(self, series, instruments, htf_list=(60, 240), warmup=150, comm_cote=1.25, slip_ticks=1):
        parts = []
        self.series = []
        off = 0
        for sid, S in enumerate(series):
            spec = instruments.get(S['racine'], {'point': 5.0, 'tick': 0.25})
            R = serie_tableaux(S, htf_list, (spec['point'], spec['tick']))
            n = S['n']
            R['sid'] = np.full(n, sid, np.int32)
            R['i'] = np.arange(n)
            R['seg_end'] = np.full(n, off + n - 1, np.int64)
            R['ok'] = (np.arange(n) >= warmup) & (R['ratr'] > 0)
            parts.append(R)
            self.series.append(dict(sid=sid, racine=S['racine'], source=S['source'], n=n, tf=S['tf'], tfm=S['tfm'],
                                    debut=S['T'][0], fin=S['T'][-1], exact=S.get('exact', 0.0), hasv=S['hasv'],
                                    off=off))
            off += n
        self.A = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
        self.N = off
        self.htf = list(htf_list)
        self.comm_cote = comm_cote
        self.slip_ticks = slip_ticks
        self.racine = np.concatenate([np.full(p['sid'].shape, s['racine'], object) for p, s in zip(parts, self.series)])
        self.jours = np.unique(self.A['jour'][self.A['ok']])
        self._piv = {}

    def pivots(self, L, R):
        """Pivots CONFIRMÉS des vrais prix (ta.pivotlow/high(r_l|r_h, L, R)) : valeur à la barre de
        confirmation (NaN sinon) et dernier swing connu (r_swLow / r_swHigh)."""
        k = (L, R)
        if k in self._piv:
            return self._piv[k]
        A = self.A
        pl = np.full(self.N, np.nan); ph = np.full(self.N, np.nan)
        for s in self.series:
            o, n = s['off'], s['n']
            lo = A['rl'][o:o + n]; hi = A['rh'][o:o + n]
            for i in range(L + R, n):
                p = i - R
                wl = np.r_[lo[p - L:p], lo[p + 1:p + R + 1]]
                wh = np.r_[hi[p - L:p], hi[p + 1:p + R + 1]]
                if (lo[p] < wl).all():
                    pl[o + i] = lo[p]
                if (hi[p] > wh).all():
                    ph[o + i] = hi[p]
        swl = np.full(self.N, np.nan); swh = np.full(self.N, np.nan)
        for s in self.series:
            o, n = s['off'], s['n']
            a = b = np.nan
            for i in range(o, o + n):
                if not np.isnan(pl[i]): a = pl[i]
                if not np.isnan(ph[i]): b = ph[i]
                swl[i] = a; swh[i] = b
        self._piv[k] = (pl, ph, swl, swh)
        return self._piv[k]

    def resume(self):
        out = []
        for s in self.series:
            out.append('%s %s min, %s -> %s, %d barres, %s%s' % (
                s['racine'], s['tf'], s['debut'].strftime('%Y-%m-%d'), s['fin'].strftime('%Y-%m-%d'), s['n'],
                {'CSV': 'vrais prix reconstitués depuis le HA', 'CSV+STD': 'vrais prix exacts (bougies standard, %.0f %%)' % (100 * s['exact']),
                 'API': 'vrais prix exacts (API)'}[s['source']], '' if s['hasv'] else ', SANS volume (pas de climax/Detector)'))
        return out
