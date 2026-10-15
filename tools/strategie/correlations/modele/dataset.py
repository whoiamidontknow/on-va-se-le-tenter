"""Tableau « état de tous les modules à chaque barre » + cibles « +1 ATR avant -1 ATR » aux VRAIS prix.

Variables : calculées sur les bougies HA (ce que voit l'indicateur), jamais sur le futur.
  - Les unités supérieures (TREND / Dashator / Heishinator HTF) sont agrégées depuis une
    reconstitution CAUSALE des vrais prix (passe avant seule de recon.py), pour éviter que le
    lissage arrière de recon.reconstruct ne fasse fuir l'information de la barre suivante.
Cible : entrée à l'ouverture de i+1 (vrai prix reconstitué, lissé = meilleure estimation),
  ATR = ATR(14) des vrais prix reconstitués ; long gagnant si high >= entrée + 1 ATR avant
  low <= entrée - 1 ATR ; les deux dans la même barre = perdant (prudent) ; non résolu en
  H barres ou coupure de séance = NaN. Short symétrique.
Séries : unités 5/15/30/60 min des CSV (MES, NQZ ; MES1 seulement avril-juillet 15m, le reste
  de MES1 recouvre MES) + API 15m avec les VRAIS prix (contrôle des artefacts de reconstitution).
"""
import sys, os, math, pickle, datetime
_STRAT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
_TOOLS = os.path.dirname(_STRAT)
sys.path.insert(0, _STRAT)
sys.path += [os.path.join(_TOOLS, d) for d in os.listdir(_TOOLS) if d.endswith('_api')]   # impl_lab_core
import numpy as np, pandas as pd
import build_all, api, features, recon
from impl_lab_core import ema_first as ema, rma
from features import PARIS

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache_dataset.pkl')
H_MAX = 60          # horizon max (barres) pour résoudre la cible
WARM = 200


# ------------------------------------------------------------------ utilitaires
def A(x):
    return np.array([np.nan if v is None else v for v in x], dtype=float)


def sma_np(x, p):
    s = pd.Series(x)
    return s.rolling(p, min_periods=p).mean().values


def bars_since(flag, cap=300):
    out = np.full(len(flag), float(cap)); last = None
    for i, f in enumerate(flag):
        if f: last = i
        if last is not None: out[i] = min(i - last, cap)
    return out


def recon_causal(bars, tick=0.25, g=None, breaks=None, eps=None):
    """recon.reconstruct sans la passe arrière : le close estimé en i n'utilise que les barres <= i."""
    n = len(bars); g = tick if g is None else g; eps = tick / 10 if eps is None else eps
    boxes = [recon._box(b, eps) for b in bars]; breaks = breaks or [False] * n
    F = [None] * n; out = []
    for i in range(n):
        fr = recon._free(boxes[i]) or (bars[i]['l'], bars[i]['h'])
        if i == 0 or breaks[i] or F[i - 1] is None:
            F[i] = fr
        else:
            r = recon._prop(F[i - 1][0] - g, F[i - 1][1] + g, boxes[i]); F[i] = r if r is not None else fr
        lo, hi = F[i]; out.append(lo + recon.pos_dir(bars, i) * (hi - lo))
    ro, rh, rl, rc = [], [], [], []
    for i in range(n):
        K, Hlo, Hhi, Llo, Lhi = boxes[i]; c = out[i]
        o = out[i - 1] if (i > 0 and not breaks[i]) else K / 4
        hk, lk = Hlo == Hhi, Llo == Lhi; h, l = Hlo, Llo
        if hk and not lk: l = min(max(K - o - c - h, Llo), min(Lhi, o, c))
        elif lk and not hk: h = max(min(K - o - c - l, Hhi), max(Hlo, o, c))
        elif not hk and not lk:
            rest = K - o - c
            h = max(min(rest / 2 + (Hhi - Lhi) / 4, Hhi), Hlo, o, c); l = min(max(rest - h, Llo), Lhi, o, c)
        o = min(max(o, l), h); c = min(max(c, l), h)
        ro.append(o); rh.append(h); rl.append(l); rc.append(c)
    return ro, rh, rl, rc


def htf_states(S, cz, m):
    """Etat de la dernière bougie de l'unité m (minutes) CLÔTURÉE à la clôture de la barre i.
    Agrégation des vrais prix CAUSAUX cz=(ro,rh,rl,rc) puis HA. TREND = close HA > EMA50 HA (>=50 barres)."""
    T = S['T']; n = S['n']; ro, rh, rl, rc = cz
    def key(t):
        if m >= 1440:
            d = t.astimezone(features.NY) + datetime.timedelta(hours=6); return (d.year, d.month, d.day)
        return int(t.timestamp() // 60) // m
    bars = []
    for i in range(n):
        k = key(T[i])
        if bars and bars[-1][0] == k:
            b = bars[-1]; bars[-1] = (k, b[1], max(b[2], rh[i]), min(b[3], rl[i]), rc[i], i)
        else:
            bars.append((k, ro[i], rh[i], rl[i], rc[i], i))
    ha = []
    for j, b in enumerate(bars):
        hc = (b[1] + b[2] + b[3] + b[4]) / 4
        ho = (b[1] + b[4]) / 2 if j == 0 else (ha[-1][0] + ha[-1][3]) / 2
        ha.append((ho, max(b[2], ho, hc), min(b[3], ho, hc), hc))
    hc = [x[3] for x in ha]; e50 = ema(hc, 50)
    s4 = [sum(x) / 4 for x in ha]; ef, es = ema(s4, 4), ema(s4, 32)
    trend = np.full(n, np.nan); dash = np.full(n, np.nan); heishi = np.full(n, np.nan); dist = np.full(n, np.nan)
    jof = []
    for j, b in enumerate(bars):
        jof += [j] * (b[5] + 1 - len(jof))
    for i in range(n):
        j = jof[i]; k = bars[j][0]
        # la bougie HTF j est clôturée à la fin de la barre i si l'heure de fin de i atteint sa fin ; sinon on prend j-1
        cur = j if (T[i].timestamp() // 60 + S['tfm'] >= (k + 1) * m) else (j - 1 if j >= 1 else None)
        if cur is not None:
            if cur >= 32: heishi[i] = float(ef[cur] > es[cur]); dash[i] = float(ha[cur][3] > ha[cur][0])
            if cur >= 50: trend[i] = float(hc[cur] > e50[cur]); dist[i] = hc[cur] - e50[cur]
    return trend, dash, heishi, dist


def trendlines_levels(h, l, bars=10, buf=0.001, nT=3, newH=100):
    """Port de features.trendline_breaks qui renvoie aussi la valeur de la droite ACTIVE à chaque barre."""
    n = len(h); ph = features.pivots(h, bars); pl = features.pivots([-v for v in l], bars)
    lev = {'r': np.full(n, np.nan), 's': np.full(n, np.nan)}; brk = {'r': np.zeros(n, bool), 's': np.zeros(n, bool)}
    for side in ('r', 's'):
        X = h if side == 'r' else [-v for v in l]; P = ph if side == 'r' else pl
        ancH = ancB = lastH = lastB = None; X1 = Y1 = X2 = Y2 = None; validAt = None; active = False
        for i in range(n):
            p = P[i]
            if p is not None and (ancH is None or p > ancH or i - ancB > newH):
                ancH, ancB = p, i - bars; lastH = lastB = None
            elif p is not None and i - bars > ancB and p < ancH:
                lastH, lastB = p, i - bars
            cH = cB = None
            if ancH is not None and lastB is not None and X[i] < ancH: cH, cB = lastH, lastB
            if cB is not None and i - ancB < 4900:
                tc = 0; ok = True
                for k in range(0, i - ancB + 1):
                    x = i - k; pv = ancH + (cH - ancH) / (cB - ancB) * (x - ancB)
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
                if side == 'r' and h[i] > v * (1 + buf): brk['r'][i] = True; active = False
                elif side == 's' and l[i] < (-v) * (1 - buf): brk['s'][i] = True; active = False
                else: lev[side][i] = v if side == 'r' else -v
    return lev['r'], lev['s'], brk['r'], brk['s']


# ------------------------------------------------------------------ variables
def feats(S, tick):
    n = S['n']; T = S['T']
    o, h, l, c = A(S['o']), A(S['h']), A(S['l']), A(S['c'])
    v = A(S['v']); va = np.array(S['va']); atr = A(S['atr']); X = {}
    vma = sma_np(v, 20)
    # Heishinator
    src = (o + h + l + c) / 4; ef, es = A(ema(list(src), 4)), A(ema(list(src), 32))
    X['heishi_bull'] = np.array(S['bull'], float)
    X['heishi_age'] = np.log1p(np.minimum(np.array(S['run'], float), 200))
    X['heishi_spread'] = (ef - es) / atr
    # Moyenator
    e50, e60 = A(S['e50']), A(S['e60'])
    X['moy_dist50'] = (c - e50) / atr; X['moy_dist60'] = (c - e60) / atr
    X['moy_pente50'] = (e50 - np.roll(e50, 5)) / atr; X['moy_pente50'][:5] = np.nan
    X['moy_e50_gt_e60'] = (e50 > e60).astype(float)
    # Signator : score 4 termes à CHAQUE barre + flèches
    score = np.full(n, np.nan); MT = 0.25
    bull = S['bull']
    for i in range(1, n):
        if np.isnan(atr[i]) or not va[i] or np.isnan(vma[i]): continue
        rng = h[i] - l[i]; rs = max(rng, MT)
        cpos = (c[i] - l[i]) / rs if bull[i] else (h[i] - c[i]) / rs
        aw = (h[i] - c[i]) / rs if bull[i] else (c[i] - l[i]) / rs
        br = min(abs(c[i] - o[i]) / rs / .5, 1)
        sS = (br + (1 - min(aw / .35, 1)) + min(cpos / .67, 1)) / 3
        sM = min(rng / max(.5 * atr[i], MT), 1)
        sV = min(v[i] / vma[i], 1) if vma[i] > 0 else 0
        sG = min(abs(o[i] - c[i - 1]) / max(.3 * atr[i], MT), 1)
        score[i] = (sS + sM + sV + sG) / 4 * 100
    X['sig_score'] = score
    sig = S['sig']
    sdir = np.array([0 if not x else x[1] for x in sig], float)
    X['sig_fort'] = np.array([0 if not x or x[0] != 'F' else x[1] for x in sig], float)
    X['sig_moyen'] = np.array([0 if not x or x[0] != 'M' else x[1] for x in sig], float)
    X['sig_age_long'] = np.log1p(bars_since(sdir > 0)); X['sig_age_short'] = np.log1p(bars_since(sdir < 0))
    # ADX
    adx, dip, dim = A(S['adx']), A(S['dip']), A(S['dim'])
    X['adx'] = adx; X['di_diff'] = dip - dim
    # Trendlines
    rl_, sl_, rB, sB = trendlines_levels(list(h), list(l))
    X['tl_dist_res'] = np.clip((rl_ - c) / atr, -20, 20); X['tl_dist_sup'] = np.clip((c - sl_) / atr, -20, 20)
    X['tl_age_cass_haut'] = np.log1p(bars_since(rB)); X['tl_age_cass_bas'] = np.log1p(bars_since(sB))
    # Detector
    dB = np.full(n, np.nan); dS = np.full(n, np.nan); inB = np.zeros(n); inS = np.zeros(n)
    for i in range(n):
        if S['Zb'][i]:
            dB[i] = min((c[i] - top) / atr[i] for top, btm in S['Zb'][i]) if atr[i] == atr[i] else np.nan
            inB[i] = float(any(btm <= c[i] <= top for top, btm in S['Zb'][i]))
        if S['Zs'][i]:
            dS[i] = min((btm - c[i]) / atr[i] for top, btm in S['Zs'][i]) if atr[i] == atr[i] else np.nan
            inS[i] = float(any(btm <= c[i] <= top for top, btm in S['Zs'][i]))
    if not S['hasv']: inB[:] = np.nan; inS[:] = np.nan
    X['det_dist_bull'] = np.clip(dB, -20, 20); X['det_dist_bear'] = np.clip(dS, -20, 20)
    X['det_in_bull'] = inB; X['det_in_bear'] = inS
    X['det_age_mit_bull'] = np.log1p(bars_since(S['mitB'])) if S['hasv'] else np.full(n, np.nan)
    X['det_age_mit_bear'] = np.log1p(bars_since(S['mitS'])) if S['hasv'] else np.full(n, np.nan)
    # Climax
    clx = np.array(S['clx'], float)
    X['clx_age_buy'] = np.log1p(bars_since(clx > 0)) if S['hasv'] else np.full(n, np.nan)
    X['clx_age_sell'] = np.log1p(bars_since(clx < 0)) if S['hasv'] else np.full(n, np.nan)
    # Sessions + Monday H/L
    for k in ('AS', 'LD', 'US'):
        hi = A([None if x is None else x[0] for x in S['SL'][k]]); lo = A([None if x is None else x[1] for x in S['SL'][k]])
        X['sess_%s_dist_haut' % k] = np.clip((c - hi) / atr, -30, 30); X['sess_%s_dist_bas' % k] = np.clip((c - lo) / atr, -30, 30)
    mh = A([None if x is None else x[0] for x in S['MHL']]); ml = A([None if x is None else x[1] for x in S['MHL']])
    X['monday_dist_haut'] = np.clip((c - mh) / atr, -30, 30); X['monday_dist_bas'] = np.clip((c - ml) / atr, -30, 30)
    # Pivots hebdo traditionnels (semaine précédente, HA)
    wk = [t.astimezone(PARIS).isocalendar()[:2] for t in T]; P = np.full(n, np.nan); R1 = np.full(n, np.nan); S1 = np.full(n, np.nan)
    cur = None; prev = None; curk = None
    for i in range(n):
        if wk[i] != curk:
            prev = cur if (cur is not None and curk is not None) else None; cur = [h[i], l[i], c[i]]; curk = wk[i]
        else:
            cur = [max(cur[0], h[i]), min(cur[1], l[i]), c[i]]
        if prev is not None:
            p = sum(prev) / 3; P[i] = p; R1[i] = 2 * p - prev[1]; S1[i] = 2 * p - prev[0]
    X['piv_dist_P'] = np.clip((c - P) / atr, -40, 40); X['piv_pos_S1R1'] = np.clip((c - S1) / (R1 - S1), -3, 4)
    # Heure / séance / jour
    hh = np.array([t.astimezone(PARIS).hour + t.astimezone(PARIS).minute / 60 for t in T])
    X['heure_sin'] = np.sin(2 * np.pi * hh / 24); X['heure_cos'] = np.cos(2 * np.pi * hh / 24)
    ses = [__import__('engine').sess_of(t) for t in T]
    for s in ('ASIE', 'LONDRES', 'US', 'SOIR'): X['seance_' + s] = np.array([x == s for x in ses], float)
    X['jour'] = np.array([t.astimezone(PARIS).weekday() for t in T], float)
    # Volume et ATR relatifs
    vr = v / vma; vr[~va] = np.nan
    X['vol_rel'] = np.log(np.clip(vr, 0.05, 20))
    X['atr_rel'] = atr / sma_np(atr, 100); X['atr_pct'] = atr / c * 1e4
    # RSI 14, CCI 30, MACD 20/40/5, YoYo, Bull/Bear score, VIDYA trend (bloc SuperTrader)
    cs = pd.Series(c)
    d = cs.diff(); up = d.clip(lower=0).fillna(0).tolist(); dn = (-d).clip(lower=0).fillna(0).tolist()
    au, ad = A(rma(up, 14)), A(rma(dn, 14)); rsi = np.where(ad == 0, 100, 100 - 100 / (1 + au / np.where(ad == 0, 1, ad)))
    rsi[np.isnan(au)] = np.nan; X['rsi'] = rsi
    tp = (h + l + c) / 3; tps = pd.Series(tp); ma = tps.rolling(30).mean()
    md = tps.rolling(30).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    X['cci'] = np.clip(((tps - ma) / (0.015 * md)).values, -400, 400)
    m = A(ema(list(c), 20)) - A(ema(list(c), 40)); sg = A(ema(list(m), 5))
    X['macd_rel'] = m / atr; X['macd_hist_rel'] = (m - sg) / atr; X['macd_bull'] = (m > sg).astype(float)
    sma10 = sma_np(c, 10); X['yoyo'] = (c - sma10) / sma10 * 100
    basis = sma_np(c, 20); sd = cs.rolling(20).std(ddof=0).values; upBB, loBB = basis + 2 * sd, basis - 2 * sd
    e200 = A(ema(list(c), 200)); rsip = np.roll(rsi, 1); cp = np.roll(c, 1)
    xo_rsi30 = (rsi > 30) & (rsip <= 30); xu_rsi70 = (rsi < 70) & (rsip >= 70)
    xo_bb = (c > loBB) & (cp <= np.roll(loBB, 1)); xu_bb = (c < upBB) & (cp >= np.roll(upBB, 1))
    X['bull_score'] = (e50 > e200).astype(float) + xo_rsi30 + xo_bb
    X['bear_score'] = (e50 < e200).astype(float) + xu_rsi70 + xu_bb
    # VIDYA (CMO 20, période 10, SMA 15) ± 2 ATR(200)
    mo = np.r_[0, np.diff(c)]; sp = pd.Series(np.where(mo >= 0, mo, 0)).rolling(20).sum().values
    sn = pd.Series(np.where(mo < 0, -mo, 0)).rolling(20).sum().values
    cmo = np.abs(100 * (sp - sn) / np.maximum(sp + sn, 1)); al = 2 / 11; vv = np.zeros(n); prevv = 0.0
    for i in range(n):
        k = 0 if np.isnan(cmo[i]) else al * cmo[i] / 100; prevv = k * c[i] + (1 - k) * prevv; vv[i] = prevv
    vid = sma_np(vv, 15)
    tr = np.r_[h[0] - l[0], np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])]
    atr200 = A(rma(list(tr), 200)); ub, lb = vid + 2 * atr200, vid - 2 * atr200
    tu = np.full(n, np.nan); st = 0.0
    for i in range(1, n):
        if np.isnan(ub[i]) or np.isnan(ub[i - 1]): continue
        if c[i] > ub[i] and c[i - 1] <= ub[i - 1]: st = 1.0
        elif c[i] < lb[i] and c[i - 1] >= lb[i - 1]: st = 0.0
        tu[i] = st
    X['vidya_up'] = tu; X['vidya_dist'] = (c - vid) / atr
    # Mouvement récent HA
    X['ret1'] = (c - np.roll(c, 1)) / atr; X['ret5'] = (c - np.roll(c, 5)) / atr; X['ret20'] = (c - np.roll(c, 20)) / atr
    hh20 = pd.Series(h).rolling(20).max().values; ll20 = pd.Series(l).rolling(20).min().values
    X['pos_range20'] = (c - ll20) / np.maximum(hh20 - ll20, 1e-9)
    X['corps_ha'] = (c - o) / np.maximum(h - l, 1e-9)
    # TREND / Dashator / Heishinator multi-unités (vrais prix causaux)
    brk = S['brk']
    cz = recon_causal([dict(o=o[i], h=h[i], l=l[i], c=c[i]) for i in range(n)], tick=tick, g=tick, breaks=brk)
    for lab, mult in (('htf1', 4), ('htf2', 16)):
        tr_, da_, he_, di_ = htf_states(S, cz, S['tfm'] * mult)
        X['trend_' + lab] = tr_; X['dash_' + lab] = da_; X['heishi_' + lab] = he_; X['trend_dist_' + lab] = di_ / atr
    X['unite_log'] = np.full(n, math.log(S['tfm']))
    df = pd.DataFrame(X)
    df[~np.isfinite(df)] = np.nan
    return df


# ------------------------------------------------------------------ cibles
def targets(S, rh=None, rl=None, ro=None, ratr=None):
    n = S['n']; rh = A(S['rh'] if rh is None else rh); rl = A(S['rl'] if rl is None else rl)
    ro = A(S['ro'] if ro is None else ro); atr = A(S['ratr'] if ratr is None else ratr); brk = S['brk']
    yL = np.full(n, np.nan); yS = np.full(n, np.nan); tL = np.full(n, np.nan); tS = np.full(n, np.nan)
    for i in range(n - 1):
        a = atr[i]
        if np.isnan(a) or a <= 0 or brk[i + 1]: continue
        e = ro[i + 1]; doneL = doneS = False
        for j in range(i + 1, min(n, i + 1 + H_MAX)):
            if j > i + 1 and brk[j]: break
            up = rh[j] >= e + a; dn = rl[j] <= e - a
            if not doneL and (up or dn): yL[i] = 1.0 if (up and not dn) else 0.0; tL[i] = j; doneL = True
            if not doneS and (up or dn): yS[i] = 1.0 if (dn and not up) else 0.0; tS[i] = j; doneS = True
            if doneL and doneS: break
    return yL, yS, tL, tS


def one(S, name, sym, tick, true_prices=None):
    df = feats(S, tick)
    yL, yS, tL, tS = targets(S)
    df['yL'] = yL; df['yS'] = yS
    tt = np.array([t.timestamp() for t in S['T']])
    df['t'] = tt
    df['t_resL'] = [tt[int(j)] if j == j else np.nan for j in tL]
    df['t_resS'] = [tt[int(j)] if j == j else np.nan for j in tS]
    if true_prices is not None:
        yLt, ySt, _, _ = targets(S, *true_prices)
        df['yL_vrai'] = yLt; df['yS_vrai'] = ySt
    df['serie'] = name; df['sym'] = sym; df['tfm'] = S['tfm']; df['i'] = np.arange(S['n'])
    return df.iloc[WARM:].reset_index(drop=True)


def build():
    out = []
    for S in build_all.load():
        if S['tfm'] not in (5, 15, 30, 60): continue
        if S['sym'] == 'MES1' and not (S['tfm'] == 15 and S['T'][0].month < 8): continue
        name = '%s_%s_%s' % (S['sym'], S['tf'], S['T'][0].strftime('%m%d'))
        sym = 'NQ' if S['sym'] == 'NQZ' else 'MES'
        out.append(one(S, name, sym, 0.25)); print(name, len(out[-1]))
    for S in api.series('15m', 'recon'):
        # signaux HA + vrais prix reconstitués (recon) ; on ajoute les cibles aux VRAIS prix de l'API
        seg = api.load_rows('15m'); seg = [s for s in seg if len(s) >= 300][0]
        rc = [r['cr'] for r in seg]; rh = [r['hr'] for r in seg]; rl = [r['lr'] for r in seg]
        ro = [4 * r['c'] - r['hr'] - r['lr'] - r['cr'] for r in seg]
        ratr = features.adx_atr(rh, rl, rc)[0]
        out.append(one(S, 'API_15', 'API', 1.0, true_prices=(rh, rl, ro, ratr))); print('API_15', len(out[-1]))
    D = pd.concat(out, ignore_index=True)
    pickle.dump(D, open(CACHE, 'wb'))
    return D


def load():
    return pickle.load(open(CACHE, 'rb')) if os.path.exists(CACHE) else build()


FEATS_EXCL = {'yL', 'yS', 't', 't_resL', 't_resS', 'yL_vrai', 'yS_vrai', 'serie', 'sym', 'tfm', 'i'}


def feat_cols(D):
    return [k for k in D.columns if k not in FEATS_EXCL]


if __name__ == '__main__':
    if os.path.exists(CACHE): os.remove(CACHE)
    D = build()
    print(D.shape)
    print(D.groupby('serie')[['yL', 'yS']].agg(['mean', 'count']).round(3))
    A_ = D[D.serie == 'API_15']
    ok = A_[['yL', 'yL_vrai']].dropna(); okS = A_[['yS', 'yS_vrai']].dropna()
    print('API : accord cible recon/vrai long %.3f (n=%d), short %.3f (n=%d)' % (
        (ok.yL == ok.yL_vrai).mean(), len(ok), (okS.yS == okS.yS_vrai).mean(), len(okS)))
    print(D[feat_cols(D)].isna().mean().round(2).sort_values().to_string())
