"""Tableau barre par barre : état de TOUS les modules + cibles aux VRAIS prix.

Réutilise tools/strategie (build_all = séries CSV fusionnées + vrais prix reconstitués, api = vrais prix,
features = modules, strat = filtres/Feu). Rien n'est recalculé ici qui existe déjà là-bas, sauf :
  - la valeur de la droite de tendance active (features.trendline_breaks ne la renvoie pas) : copie
    instrumentée, vérifiée identique sur les cassures (assert) ;
  - le score Signator (non conservé par build_series) : même formule à 4 termes.

Unités : MES/NQ 5-60 min (CSV, prix reconstitués), MES1 15 min avr-jul (sans volume), API 15m/2m (vrais prix).
Sortie : table.pkl (DataFrame) + series.pkl (séries S, pour engine.run).
"""
import sys, os, math, pickle, datetime
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
import build_all, api, features, strat, engine
from features import ema, rma, sma, pivots, PARIS, NY

OUT = os.path.join(HERE, 'table.pkl')
OUTS = os.path.join(HERE, 'series.pkl')
WARM = 150
HMAX = 64            # horizon max pour les barrières


# ------------------------------------------------------------------ droite active (copie instrumentée)
def trendline_levels(h, l, bars=10, buf=0.001, nT=3, newH=100):
    n = len(h)
    ph = pivots(h, bars); pl = pivots([-v for v in l], bars)
    rB = [False] * n; sB = [False] * n; rV = [None] * n; sV = [None] * n
    for side in ('r', 's'):
        X = h if side == 'r' else [-v for v in l]
        P = ph if side == 'r' else pl
        ancH = ancB = lastH = lastB = None
        X1 = Y1 = X2 = Y2 = None; validAt = None; active = False
        for i in range(n):
            p = P[i]
            if p is not None and (ancH is None or p > ancH or i - ancB > newH):
                ancH, ancB = p, i - bars; lastH = lastB = None
            elif p is not None and i - bars > ancB and p < ancH:
                lastH, lastB = p, i - bars
            cH = cB = None
            if ancH is not None and lastB is not None and X[i] < ancH:
                cH, cB = lastH, lastB
            if cB is not None and i - ancB < 4900:
                tc = 0; ok = True
                for k in range(0, i - ancB + 1):
                    x = i - k
                    pv = ancH + (cH - ancH) / (cB - ancB) * (x - ancB)
                    if side == 'r':
                        if h[x] > pv * (1 + buf): ok = False; break
                        if h[x] >= pv * (1 - buf): tc += 1
                    else:
                        lv = -pv
                        if l[x] < lv * (1 - buf): ok = False; break
                        if l[x] <= lv * (1 + buf): tc += 1
                if ok and tc >= nT and (X1 is None or X1 != ancB or X2 != cB):
                    X1, Y1, X2, Y2 = ancB, ancH, cB, cH; validAt = i; active = True
            if active and X1 is not None and i > validAt:
                v = Y1 + (Y2 - Y1) / (X2 - X1) * (i - X1)
                if side == 'r':
                    rV[i] = v
                    if h[i] > v * (1 + buf): rB[i] = True; active = False
                else:
                    sV[i] = -v
                    if l[i] < (-v) * (1 - buf): sB[i] = True; active = False
    return rB, sB, rV, sV


# ------------------------------------------------------------------ indicateurs du tableau principal
def rsi(c, p=14):
    n = len(c)
    up = [0.0] + [max(c[i] - c[i - 1], 0) for i in range(1, n)]; dn = [0.0] + [max(c[i - 1] - c[i], 0) for i in range(1, n)]
    au, ad = rma(up, p), rma(dn, p)
    return [None if a is None else (100.0 if b == 0 else 100 - 100 / (1 + a / b)) for a, b in zip(au, ad)]


def cci(h, l, c, p=30):
    tp = pd.Series([(a + b + d) / 3 for a, b, d in zip(h, l, c)])
    m = tp.rolling(p).mean()
    md = tp.rolling(p).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return ((tp - m) / (0.015 * md)).tolist()


def vidya_trend(c, h, l, per=10, mom=20, band=2.0):
    n = len(c); cs = pd.Series(c)
    ch = cs.diff().fillna(0)
    sp = ch.clip(lower=0).rolling(mom).sum(); sn = (-ch.clip(upper=0)).rolling(mom).sum()
    cmo = (100 * (sp - sn) / np.maximum(sp + sn, 1)).abs().fillna(0).values
    a = 2.0 / (per + 1); v = 0.0; vr = []
    for i in range(n):
        v = a * cmo[i] / 100 * c[i] + (1 - a * cmo[i] / 100) * v; vr.append(v)
    vid = pd.Series(vr).rolling(15).mean().values
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]
    a200 = rma(tr, 200)
    up = False; out = [None] * n; pu = pl = None
    for i in range(n):
        if a200[i] is None or np.isnan(vid[i]): continue
        ub, lb = vid[i] + band * a200[i], vid[i] - band * a200[i]
        if pu is not None:
            if c[i] > ub and c[i - 1] <= pu: up = True
            elif c[i] < lb and c[i - 1] >= pl: up = False
        pu, pl = ub, lb; out[i] = up
    return out


def macd_state(c, f=20, s=40, g=5):
    m = [a - b for a, b in zip(ema(c, f), ema(c, s))]; sg = ema(m, g)
    st = []
    for a, b in zip(m, sg):
        bull = a > b
        st.append(2 if (bull and a > -0.25 and b > -0.25) else (0 if (not bull and a > -0.025 and b > -0.025) else (1 if bull else -1)))
    return m, sg, st


def bull_bear(c, r):
    n = len(c); e50, e200 = ema(c, 50), ema(c, 200)
    cs = pd.Series(c); bas = cs.rolling(20).mean(); sd = cs.rolling(20).std(ddof=0)
    up, lo = (bas + 2 * sd).values, (bas - 2 * sd).values
    out = [None] * n
    for i in range(1, n):
        if r[i] is None or r[i - 1] is None or np.isnan(up[i - 1]): continue
        bc = (e50[i] > e200[i]) + (r[i] > 30 >= r[i - 1]) + (c[i] > lo[i] and c[i - 1] <= lo[i - 1])
        sc = (e50[i] < e200[i]) + (r[i] < 70 <= r[i - 1]) + (c[i] < up[i] and c[i - 1] >= up[i - 1])
        out[i] = int(bc) - int(sc)
    return out


# ------------------------------------------------------------------ unités supérieures (CSV de la même famille)
def inst(sym):
    return 'MES' if sym in ('MES', 'MES1') else ('NQ' if sym == 'NQZ' else sym)


def htf_index(S_all):
    """Par (instrument, tfm) : temps de clôture triés + états (trend, dash, heishi) de la bougie CSV clôturée."""
    idx = {}
    for S in S_all:
        k = (inst(S['sym']), S['tfm'])
        tc = np.array([t.timestamp() + S['tfm'] * 60 for t in S['T']])
        tr = np.array([c > e for c, e in zip(S['c'], S['e50'])], float)
        da = np.array([c > o for c, o in zip(S['c'], S['o'])], float)
        he = np.array(S['bull'], float)
        tr[:60] = np.nan; da[:5] = np.nan; he[:40] = np.nan
        idx.setdefault(k, []).append((tc, tr, da, he))
    return idx


def map_htf(idx, ins, tfm_h, tcl):
    """tcl : temps de clôture des barres basses (s). Renvoie 3 tableaux (trend, dash, heishi) ou NaN."""
    out = np.full((3, len(tcl)), np.nan)
    for tc, tr, da, he in idx.get((ins, tfm_h), []):
        j = np.searchsorted(tc, tcl, 'right') - 1
        ok = (j >= 0) & (tcl <= tc[-1] + tfm_h * 60) & (tcl >= tc[0])
        jj = np.clip(j, 0, len(tc) - 1)
        ok &= (tcl - tc[jj]) < max(3 * tfm_h * 60, 4 * 3600) + (3 * 86400 if tfm_h < 1440 else 0)
        for r, a in enumerate((tr, da, he)):
            v = a[jj]
            out[r] = np.where(ok & ~np.isnan(v), v, out[r])
    return out


def daily_htf(S240_list):
    """TREND/Dash/Heishi 1D à partir des vrais prix 240 (features.resample_real), indexés par temps de clôture."""
    res = []
    for S in S240_list:
        f = features.resample_real(S, 1440)
        tc = np.array([t.timestamp() + S['tfm'] * 60 for t in S['T']])
        tr = np.array([np.nan if x is None else float(x['trend']) for x in f])
        da = np.array([np.nan if x is None else float(x['dash']) for x in f])
        he = np.array([np.nan if x is None else float(x['heishi']) for x in f])
        res.append((tc, tr, da, he))
    return res


# ------------------------------------------------------------------ pivots (traditionnels, HA de la période précédente)
def period_pivots(S240_list):
    """Vrais prix 240 -> barres semaine/mois/année (Paris) -> HA -> pivots P/R1/S1 de la période précédente."""
    rows = []
    for S in S240_list:
        for i in range(S['n']):
            rows.append((S['T'][i], S['ro'][i], S['rh'][i], S['rl'][i], S['rc'][i]))
    rows.sort(key=lambda r: r[0])
    out = {}
    for kind in ('W', 'M', 'Y'):
        def key(t, kind=kind):
            d = t.astimezone(PARIS)
            return d.isocalendar()[:2] if kind == 'W' else ((d.year, d.month) if kind == 'M' else d.year)
        bars = []
        for t, o, h, l, c in rows:
            k = key(t)
            if bars and bars[-1][0] == k:
                b = bars[-1]; bars[-1] = (k, b[1], max(b[2], h), min(b[3], l), c)
            else:
                bars.append((k, o, h, l, c))
        piv = {}; ho = hc = None
        for j, (k, o, h, l, c) in enumerate(bars):
            nc = (o + h + l + c) / 4; no = (o + c) / 2 if ho is None else (ho + hc) / 2
            hh, hl = max(h, no, nc), min(l, no, nc)
            if j + 1 < len(bars) and j >= 1:          # HA « chaud » d'au moins une période
                P = (hh + hl + nc) / 3
                piv[bars[j + 1][0]] = (P, 2 * P - hl, 2 * P - hh)
            ho, hc = no, nc
        out[kind] = (key, piv)
    return out


# ------------------------------------------------------------------ cibles aux vrais prix
def targets(S, real_hl=True):
    n = S['n']; ro, rh, rl, rc, a = S['ro'], S['rh'], S['rl'], S['rc'], S['ratr']
    T = S['T']; ts = np.array([t.timestamp() for t in T])
    gap = np.r_[False, np.diff(ts) > 12 * 3600]          # coupure > 12 h (week-end, trou de données)
    cg = np.cumsum(gap)
    res = {k: np.full(n, np.nan) for k in ('ret4', 'ret8', 'ret16', 'L1', 'S1', 'L15', 'S15', 'cost')}
    pv, tick = engine.SPEC[S['sym']]
    for i in range(WARM, n - 1):
        if not a[i]: continue
        e = ro[i + 1]
        res['cost'][i] = (2 * tick + engine.COMM / pv) / a[i]
        for h in (4, 8, 16):
            if i + h < n and cg[i + h] == cg[i]:
                res['ret%d' % h][i] = (rc[i + h] - e) / a[i]
        for k, nm in ((1.0, '1'), (1.5, '15')):
            up, dn = e + k * a[i], e - k * a[i]
            rl_, rs_ = np.nan, np.nan
            for j in range(i + 1, min(n, i + 1 + HMAX)):
                if cg[j] != cg[i]: break
                hu, hd = rh[j] >= up, rl[j] <= dn
                if np.isnan(rl_):
                    if hd: rl_ = 0.0          # stop touché (même barre que l'objectif : stop d'abord)
                    elif hu: rl_ = 1.0
                if np.isnan(rs_):
                    if hu: rs_ = 0.0
                    elif hd: rs_ = 1.0
                if not np.isnan(rl_) and not np.isnan(rs_): break
            res['L' + nm][i] = rl_; res['S' + nm][i] = rs_
    return res


# ------------------------------------------------------------------ construction d'une série
def series_rows(S, sid, idx, didx, piv, group):
    n = S['n']; o, h, l, c, v = S['o'], S['h'], S['l'], S['c'], S['v']
    atr = S['atr']; e50, e60 = S['e50'], S['e60']
    A = lambda x: np.array([np.nan if y is None else y for y in x], float)
    atr_a = A(atr)
    D = {}
    T = S['T']
    D['sid'] = [sid] * n; D['i'] = list(range(n)); D['sym'] = [inst(S['sym'])] * n; D['tf'] = [S['tfm']] * n
    D['group'] = [group] * n
    D['t'] = T
    D['day'] = [(t.astimezone(NY) + datetime.timedelta(hours=6)).date() for t in T]
    D['hour'] = [t.astimezone(PARIS).hour for t in T]
    D['wday'] = [t.astimezone(PARIS).weekday() for t in T]
    D['sess'] = [engine.sess_of(t) for t in T]
    # Heishinator
    D['heishi'] = [1 if b else -1 for b in S['bull']]
    D['heishi_age'] = S['run']
    # Moyenator
    D['moy_pos50'] = [1 if c[i] > e50[i] else -1 for i in range(n)]
    D['moy_band'] = [1 if c[i] > max(e50[i], e60[i]) else (-1 if c[i] < min(e50[i], e60[i]) else 0) for i in range(n)]
    D['moy_dist'] = (np.array(c) - np.array(e50)) / atr_a
    D['moy_slope'] = np.r_[[np.nan] * 5, (np.array(e50[5:]) - np.array(e50[:-5]))] / atr_a
    # Signator
    sig = S['sig']
    D['sigF'] = [x[1] if x and x[0] == 'F' else 0 for x in sig]
    D['sigM'] = [x[1] if x and x[0] == 'M' else 0 for x in sig]
    sc = np.full(n, np.nan)
    vma = sma(v, 20)
    for i in range(1, n):
        if atr[i] is None or not S['va'][i] or vma[i] is None: continue
        MT = 0.25; rng = h[i] - l[i]; rs = max(rng, MT); bl = S['bull'][i]
        cpos = (c[i] - l[i]) / rs if bl else (h[i] - c[i]) / rs
        aw = (h[i] - c[i]) / rs if bl else (c[i] - l[i]) / rs
        br = min(abs(c[i] - o[i]) / rs / .5, 1)
        sS = (br + (1 - min(aw / .35, 1)) + min(cpos / .67, 1)) / 3
        sM = min(rng / max(.5 * atr[i], MT), 1); sV = min(v[i] / vma[i], 1) if vma[i] > 0 else 0
        sG = min(abs(o[i] - c[i - 1]) / max(.3 * atr[i], MT), 1)
        sc[i] = (sS + sM + sV + sG) / 4 * 100
    D['sig_score'] = sc
    # ADX
    D['adx'] = A(S['adx']); D['di'] = np.sign(A(S['dip']) - A(S['dim']))
    # TREND / Dash / Heishi multi-unités (bougie CLÔTURÉE)
    tcl = np.array([t.timestamp() + S['tfm'] * 60 for t in T])
    ins = inst(S['sym'])
    D['trend_tf'] = np.array(D['moy_pos50'], float)
    D['dash_tf'] = [1 if c[i] > o[i] else -1 for i in range(n)]
    for th in (15, 30, 60, 240):
        if th <= S['tfm']:
            for k in ('trend', 'dash', 'heishi'): D['%s_%d' % (k, th)] = np.full(n, np.nan)
            continue
        m = map_htf(idx, ins, th, tcl) if ins in ('MES', 'NQ') else np.full((3, n), np.nan)
        if np.isnan(m[0]).mean() > 0.5 and n / (th / S['tfm']) > 60:    # repli : vrais prix ré-agrégés
            f = features.resample_real(S, th)
            m2 = np.array([[np.nan] * 3 if x is None else [x['trend'], x['dash'], x['heishi']] for x in f], float).T
            m = np.where(np.isnan(m), m2, m)
        for r, k in enumerate(('trend', 'dash', 'heishi')): D['%s_%d' % (k, th)] = 2 * m[r] - 1
    md = map_htf({(ins, 1440): didx.get(ins, [])}, ins, 1440, tcl)
    D['trend_D'] = 2 * md[0] - 1; D['dash_D'] = 2 * md[1] - 1; D['heishi_D'] = 2 * md[2] - 1
    # Trendlines
    rB, sB, rV, sV = trendline_levels(h, l)
    assert rB == S['rB'] and sB == S['sB'], 'droite instrumentée != features.trendline_breaks'
    D['tl_break'] = [1 if rB[i] else (-1 if sB[i] else 0) for i in range(n)]
    D['tl_res_dist'] = (np.array(c) - A(rV)) / atr_a     # <0 : sous la résistance active
    D['tl_sup_dist'] = (np.array(c) - A(sV)) / atr_a     # >0 : au-dessus du support actif
    # Detector
    inz = []; db = []; ds = []
    for i in range(n):
        Zb, Zs = S['Zb'][i], S['Zs'][i]
        z = 1 if any(b <= c[i] <= t for t, b in Zb) else (-1 if any(b <= c[i] <= t for t, b in Zs) else 0)
        inz.append(z)
        db.append(min([(c[i] - t) / atr[i] for t, b in Zb], key=abs) if Zb and atr[i] else np.nan)
        ds.append(min([(b - c[i]) / atr[i] for t, b in Zs], key=abs) if Zs and atr[i] else np.nan)
    hasv = S['hasv']
    D['det_in'] = inz if hasv else np.full(n, np.nan)
    D['det_dist_bull'] = db if hasv else np.full(n, np.nan)
    D['det_dist_bear'] = ds if hasv else np.full(n, np.nan)
    D['det_mit'] = [(-1 if S['mitB'][i] else (1 if S['mitS'][i] else 0)) for i in range(n)] if hasv else np.full(n, np.nan)
    reb = dict(strat.e_det_rebond(S)) if hasv else {}
    D['det_rebond'] = [reb.get(i, 0) for i in range(n)] if hasv else np.full(n, np.nan)
    # Climax
    clx = S['clx']
    D['clx'] = clx if hasv else np.full(n, np.nan)
    ab, as_ = [], []; lb = ls = None
    for i in range(n):
        if clx[i] == 1: lb = i
        if clx[i] == -1: ls = i
        ab.append(i - lb if lb is not None else np.nan); as_.append(i - ls if ls is not None else np.nan)
    D['clx_age_buy'] = ab if hasv else np.full(n, np.nan); D['clx_age_sell'] = as_ if hasv else np.full(n, np.nan)
    # Sessions et Monday
    sb = dict(strat.e_sess(S)); mb = dict(strat.e_mhl(S))
    for k in ('AS', 'LD', 'US'):
        pos = []; dh = []; dl = []
        for i in range(n):
            x = S['SL'][k][i]
            if x is None or not atr[i]: pos.append(np.nan); dh.append(np.nan); dl.append(np.nan); continue
            pos.append(1 if c[i] > x[0] else (-1 if c[i] < x[1] else 0))
            dh.append((c[i] - x[0]) / atr[i]); dl.append((c[i] - x[1]) / atr[i])
        D['sess_%s_pos' % k] = pos; D['sess_%s_dhi' % k] = dh; D['sess_%s_dlo' % k] = dl
    D['sess_break'] = [sb.get(i, 0) for i in range(n)]
    pos = []
    for i in range(n):
        x = S['MHL'][i]
        pos.append(np.nan if x is None else (1 if c[i] > x[0] else (-1 if c[i] < x[1] else 0)))
    D['mon_pos'] = pos; D['mon_break'] = [mb.get(i, 0) for i in range(n)]
    # Pivots
    for kind, nm in (('Y', 'an'), ('M', 'mois'), ('W', 'sem')):
        key, pv = piv.get(ins, {}).get(kind, (None, {}))
        P_ = np.full(n, np.nan); R_ = np.full(n, np.nan); S_ = np.full(n, np.nan)
        if key is not None:
            for i in range(n):
                x = pv.get(key(T[i]))
                if x: P_[i], R_[i], S_[i] = x
        cc = np.array(c)
        D['piv_%s_P' % nm] = (cc - P_) / atr_a; D['piv_%s_R1' % nm] = (cc - R_) / atr_a; D['piv_%s_S1' % nm] = (cc - S_) / atr_a
        D['piv_%s_zone' % nm] = np.where(np.isnan(P_), np.nan, np.where(cc > R_, 2, np.where(cc > P_, 1, np.where(cc > S_, -1, -2))))
    # Volume / ATR relatifs
    D['vol_rel'] = [v[i] / vma[i] if (S['va'][i] and vma[i]) else np.nan for i in range(n)]
    asma = pd.Series(atr_a).rolling(100).mean().values
    D['atr_rel'] = atr_a / asma
    # Tableau principal
    r = rsi(c); D['rsi'] = A(r)
    D['cci'] = cci(h, l, c, 30)
    m_, sg_, st_ = macd_state(c); D['macd_state'] = st_; D['macd_dir'] = [1 if a > b else -1 for a, b in zip(m_, sg_)]
    s10 = pd.Series(c).rolling(10).mean().values
    D['yoyo'] = (np.array(c) - s10) / s10 * 100
    D['bullbear'] = A(bull_bear(c, r))
    vt = vidya_trend(c, h, l); D['vidya'] = [np.nan if x is None else (1 if x else -1) for x in vt]
    strat.ensure_feu(S); D['feu'] = A(S['feu'])
    # Cibles
    tg = targets(S)
    for k, x in tg.items(): D[k] = x
    df = pd.DataFrame(D)
    return df.iloc[WARM:].reset_index(drop=True)


def build():
    S_csv = build_all.load()
    lo = [s for s in S_csv if s['tfm'] in (5, 15, 30, 60) and (s['sym'] != 'MES1' or (s['tfm'] == 15 and s['T'][0].month < 8))]
    hi = [s for s in S_csv if s['tfm'] in (15, 30, 60, 240) and not (s['sym'] == 'MES1' and s['tfm'] == 15 and s['T'][0].month < 8)] + \
         [s for s in S_csv if s['sym'] == 'MES1' and s['tfm'] == 15 and s['T'][0].month < 8]
    idx = htf_index(hi)
    s240 = {'MES': [s for s in S_csv if s['tfm'] == 240 and s['sym'] in ('MES', 'MES1')],
            'NQ': [s for s in S_csv if s['tfm'] == 240 and s['sym'] == 'NQZ']}
    didx = {k: daily_htf(v) for k, v in s240.items()}
    piv = {k: period_pivots(v) for k, v in s240.items()}
    A15 = api.series('15m', 'vrai'); A2 = api.series('2m', 'vrai')
    allS = []; dfs = []
    todo = [(s, 'MES1avr-jul' if s['sym'] == 'MES1' else inst(s['sym'])) for s in lo] + \
           [(s, 'API15') for s in A15] + [(s, 'API2') for s in A2]
    for s, g in todo:
        sid = len(allS); allS.append(s)
        df = series_rows(s, sid, idx, didx, piv, g)
        dfs.append(df)
        print(g, s['tf'], s['n'], 'lignes', len(df), 'ret8 ok', df['ret8'].notna().sum(), flush=True)
    df = pd.concat(dfs, ignore_index=True)
    pickle.dump(df, open(OUT, 'wb')); pickle.dump(allS, open(OUTS, 'wb'))
    return df, allS


def load():
    if not os.path.exists(OUT): return build()
    return pickle.load(open(OUT, 'rb')), pickle.load(open(OUTS, 'rb'))


if __name__ == '__main__':
    df, S = build()
    print(df.shape)
    print(df.describe().T.to_string())
