"""Calcul, sur chaque série HA fusionnée, des signaux de CompletV3 / CLIMATOR et des vrais prix reconstitués.

Signaux (calculés sur HA, comme l'indicateur) :
  bull/run (Heishinator EMA(ohlc4,4) > EMA(ohlc4,32)), Signator Fort/Moyen V9 + blackout,
  cassures de trendlines (mèche + tampon 0,1 %), zones Detector (OB LuxAlgo, mitigation mèche),
  climax (CLIMATOR), sessions Asie/Londres/US, Monday High/Low (lundi 00:00 -> mardi 07:30 Paris),
  ADX, Moyenator EMA50/60, TREND multi-unités et « Feu » simplifié (proxy, voir plus bas).
Vrais prix : recon.reconstruct (validé sur l'API).
"""
import sys, datetime, math
sys.path.insert(0, '/Users/jeremk/ERGON/on-va-se-le-tenter/tools/ephore_api')
from impl_lab_core import ema_first as ema, rma
from zoneinfo import ZoneInfo
import recon

NY = ZoneInfo('America/New_York'); PARIS = ZoneInfo('Europe/Paris')
TOKYO = ZoneInfo('Asia/Tokyo'); LONDON = ZoneInfo('Europe/London')
TFMIN = {'1': 1, '2': 2, '3': 3, '5': 5, '15': 15, '30': 30, '60': 60, '240': 240, '720': 720, '1D': 1440}


def sma(x, p):
    out = [None] * len(x); s = 0.0
    for i, v in enumerate(x):
        s += v
        if i >= p: s -= x[i - p]
        if i >= p - 1: out[i] = s / p
    return out


def adx_atr(h, l, c, p=14):
    n = len(c)
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]
    atr = rma(tr, p)
    up = [0] + [h[i] - h[i - 1] for i in range(1, n)]; dn = [0] + [l[i - 1] - l[i] for i in range(1, n)]
    pdm = [u if (u > d and u > 0) else 0.0 for u, d in zip(up, dn)]
    mdm = [d if (d > u and d > 0) else 0.0 for u, d in zip(up, dn)]
    ps = rma(pdm, p); ms = rma(mdm, p)
    dip = [100 * a / b if a is not None and b else None for a, b in zip(ps, atr)]
    dim = [100 * a / b if a is not None and b else None for a, b in zip(ms, atr)]
    dx = [None if a is None else abs(a - b) / ((a + b) or 1) * 100 for a, b in zip(dip, dim)]
    return atr, rma(dx, p), dip, dim


def pivots(x, L, strict=True):
    """pivot haut confirmé à la barre i (pivot en i-L). Renvoie liste de (i, valeur) indexée par i."""
    n = len(x); out = [None] * n
    for i in range(2 * L, n):
        p = i - L; v = x[p]
        ok = all(v > x[k] for k in range(p - L, p)) and all(v > x[k] for k in range(p + 1, p + L + 1))
        if ok: out[i] = v
    return out


def trendline_breaks(h, l, bars=10, buf=0.001, nT=3, newH=100):
    """Port de TRENDLINES V2. Renvoie (rBreak[i], sBreak[i]) : cassure haussière de la résistance, baissière du support."""
    n = len(h)
    ph = pivots(h, bars); pl = pivots([-v for v in l], bars)
    rB = [False] * n; sB = [False] * n
    for side in ('r', 's'):
        X = h if side == 'r' else [-v for v in l]
        P = ph if side == 'r' else pl
        bufS = buf
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
                        if h[x] > pv * (1 + bufS): ok = False; break
                        if h[x] >= pv * (1 - bufS): tc += 1
                    else:
                        lv = -pv
                        if l[x] < lv * (1 - bufS): ok = False; break
                        if l[x] <= lv * (1 + bufS): tc += 1
                if ok and tc >= nT and (X1 is None or X1 != ancB or X2 != cB):
                    X1, Y1, X2, Y2 = ancB, ancH, cB, cH; validAt = i; active = True
            if active and X1 is not None and i > validAt:
                v = Y1 + (Y2 - Y1) / (X2 - X1) * (i - X1)
                if side == 'r' and h[i] > v * (1 + buf):
                    rB[i] = True; active = False
                if side == 's' and l[i] < (-v) * (1 - buf):
                    sB[i] = True; active = False
    return rB, sB


def detector(o, h, l, c, v, length=5, keep=3):
    """OB LuxAlgo (Detector). Renvoie pour chaque barre la liste des zones bull/bear actives (top, btm),
    et les événements de mitigation (cassure de zone)."""
    n = len(c)
    hl2 = [(a + b) / 2 for a, b in zip(h, l)]
    phv = pivots(v, length)
    os_ = 0; bull = []; bear = []
    Zb = [None] * n; Zs = [None] * n; mitB = [False] * n; mitS = [False] * n
    for i in range(n):
        if i < 2 * length:
            Zb[i] = []; Zs[i] = []; continue
        upper = max(h[i - length + 1:i + 1]); lower = min(l[i - length + 1:i + 1])
        os_ = 0 if h[i - length] > upper else (1 if l[i - length] < lower else os_)
        if phv[i] is not None and min(v[i - 2 * length:i + 1]) < 0: phv[i] = None
        if phv[i] is not None and os_ == 1:
            bull.insert(0, (hl2[i - length], l[i - length]))
        if phv[i] is not None and os_ == 0:
            bear.insert(0, (h[i - length], hl2[i - length]))
        nb = [z for z in bull if not (lower < z[1])]
        if len(nb) < len(bull): mitB[i] = True
        bull = nb
        ns = [z for z in bear if not (upper > z[0])]
        if len(ns) < len(bear): mitS[i] = True
        bear = ns
        Zb[i] = bull[:keep]; Zs[i] = bear[:keep]
    return Zb, Zs, mitB, mitS


def news(t, tfm):
    if tfm >= 1440: return False
    d = t.astimezone(NY); m = d.hour * 60 + d.minute
    return abs(m - 510) <= 3 or abs(m - 600) <= 3


def in_sess(t, tz, a, b):
    d = t.astimezone(tz); m = d.hour * 60 + d.minute
    return a <= m < b


def build_series(seg, tf, sym, g=0.25, tick=0.25):
    tfm = TFMIN[tf]
    n = len(seg)
    T = [r['t'] for r in seg]
    o = [r['o'] for r in seg]; h = [r['h'] for r in seg]; l = [r['l'] for r in seg]; c = [r['c'] for r in seg]
    vraw = [r['v'] for r in seg]
    v = [x if x is not None else 0.0 for x in vraw]
    va = [i >= 19 and all(x is not None for x in vraw[i - 19:i + 1]) for i in range(n)]   # volume connu sur 20 barres
    hasv = sum(va) > 0.5 * n
    src = [(o[i] + h[i] + l[i] + c[i]) / 4 for i in range(n)]
    ef, es = ema(src, 4), ema(src, 32)
    bull = [a > b for a, b in zip(ef, es)]
    run = [1] * n
    for i in range(1, n): run[i] = run[i - 1] + 1 if bull[i] == bull[i - 1] else 1
    e50, e60 = ema(c, 50), ema(c, 60)
    atr, adx, dip, dim = adx_atr(h, l, c)
    vma = sma(v, 20)
    # --- Signator V9 + blackout (score 4 termes)
    sig = [None] * n
    for i in range(1, n):
        if atr[i] is None or adx[i] is None or vma[i] is None: continue
        if not va[i]:   # volume inconnu : flèche de l'original exportée
            r = seg[i]
            sig[i] = ('F', 1) if r['oLF'] else ('F', -1) if r['oSF'] else ('M', 1) if r['oLM'] else ('M', -1) if r['oSM'] else None
            continue
        MT = 0.25
        rng = h[i] - l[i]; rs = max(rng, MT)
        cpos = (c[i] - l[i]) / rs if bull[i] else (h[i] - c[i]) / rs
        aw = (h[i] - c[i]) / rs if bull[i] else (c[i] - l[i]) / rs
        br = min(abs(c[i] - o[i]) / rs / .5, 1)
        sS = (br + (1 - min(aw / .35, 1)) + min(cpos / .67, 1)) / 3
        sM = min(rng / max(.5 * atr[i], MT), 1)
        sV = min(v[i] / vma[i], 1) if vma[i] > 0 else 0
        sG = min(abs(o[i] - c[i - 1]) / max(.3 * atr[i], MT), 1)
        score = (sS + sM + sV + sG) / 4 * 100
        dB = (c[i] - max(e50[i], e60[i])) / atr[i] if bull[i] else (min(e50[i], e60[i]) - c[i]) / atr[i]
        base = (run[i] == 2 and adx[i] >= 18 and (c[i] > e50[i] if bull[i] else c[i] < e50[i])
                and (dB >= 0.3 or v[i] >= vma[i]) and (rng >= 0.5 * atr[i] or cpos >= 0.67) and not news(T[i], tfm))
        if base and score >= 18:
            sig[i] = ('F' if score >= 50 else 'M', 1 if bull[i] else -1)
    # --- climax
    clx = [0] * n
    if hasv:
        for i in range(n):
            rg = h[i] - l[i]
            if rg <= 0 or not va[i] or vma[i] is None or vma[i] <= 0: continue
            body = (c[i] - o[i]) / rg; vr = v[i] / vma[i]
            if o[i] - l[i] <= 1e-6 and body >= .55 and vr >= 1.5: clx[i] = 1
            elif h[i] - o[i] <= 1e-6 and -body >= .65 and vr >= 2.0: clx[i] = -1
    # --- trendlines
    rB, sB = trendline_breaks(h, l)
    # --- detector
    if hasv:
        Zb, Zs, mitB, mitS = detector(o, h, l, c, [x if x is not None else -1.0 for x in vraw])
    else:
        Zb = Zs = [[] for _ in range(n)]; mitB = mitS = [False] * n
    # --- sessions (niveaux de la dernière session terminée) et Monday HL
    sess_def = {'AS': (TOKYO, 540, 930), 'LD': (LONDON, 480, 990), 'US': (NY, 570, 960)}
    SL = {k: [None] * n for k in sess_def}   # (high, low) de la dernière session terminée
    for k, (tz, a, b) in sess_def.items():
        cur = None; last = None; prevIn = False
        for i in range(n):
            inS = tfm < 1440 and in_sess(T[i], tz, a, b)
            if inS and not prevIn: cur = [h[i], l[i]]
            elif inS and cur: cur[0] = max(cur[0], h[i]); cur[1] = min(cur[1], l[i])
            if not inS and prevIn and cur: last = tuple(cur); cur = None
            SL[k][i] = last; prevIn = inS
    MHL = [None] * n; cur = None; wk = None; done = None
    for i in range(n):
        d = T[i].astimezone(PARIS); m = d.hour * 60 + d.minute
        inF = d.weekday() == 0 or (d.weekday() == 1 and m < 450)
        if d.weekday() == 0 and (wk is None or wk != d.isocalendar()[:2]):
            wk = d.isocalendar()[:2]; cur = [h[i], l[i]]; done = None
        elif inF and cur: cur[0] = max(cur[0], h[i]); cur[1] = min(cur[1], l[i])
        if not inF and cur is not None and done is None and wk == d.isocalendar()[:2]: done = tuple(cur)
        if wk != d.isocalendar()[:2]: done = None; cur = None
        MHL[i] = done
    # --- vrais prix
    brk = [False] + [(T[i] - T[i - 1]).total_seconds() > 1.5 * tfm * 60 for i in range(1, n)]
    R = recon.reconstruct([dict(o=o[i], h=h[i], l=l[i], c=c[i]) for i in range(n)], tick=tick, g=g, breaks=brk)
    rh = [x['rh'] for x in R]; rl = [x['rl'] for x in R]; rc = [x['rc'] for x in R]; ro = [x['ro'] for x in R]
    ratr, _, _, _ = adx_atr(rh, rl, rc)
    # bornes prudentes quand le vrai high/low n'est pas connu exactement
    rhx = [x['rh'] if x['hk'] else max(x['Hhi'], x['rh']) for x in R]      # high le plus haut possible
    rlx = [x['rl'] if x['lk'] else min(x['Llo'], x['rl']) for x in R]      # low le plus bas possible
    rhn = [x['rh'] if x['hk'] else max(x['ro'], x['rc']) for x in R]       # high le plus bas plausible
    rln = [x['rl'] if x['lk'] else min(x['ro'], x['rc']) for x in R]
    return dict(sym=sym, tf=tf, tfm=tfm, n=n, T=T, o=o, h=h, l=l, c=c, v=v, hasv=hasv, va=va, bull=bull, run=run,
                e50=e50, e60=e60, atr=atr, adx=adx, dip=dip, dim=dim, sig=sig, clx=clx, rB=rB, sB=sB,
                Zb=Zb, Zs=Zs, mitB=mitB, mitS=mitS, SL=SL, MHL=MHL, brk=brk,
                ro=ro, rh=rh, rl=rl, rc=rc, ratr=ratr, R=R, rhx=rhx, rlx=rlx, rhn=rhn, rln=rln)


def resample_real(S, tfm2):
    """Agrège les vrais prix reconstitués en unité supérieure puis calcule HA + TREND/Dashator/Heishi.
    Renvoie une fonction f(i) -> dict d'états de la dernière bougie HTF CLÔTURÉE à la clôture de la barre i."""
    T = S['T']; tfm = S['tfm']; n = S['n']
    def key(t):
        if tfm2 >= 1440:
            d = t.astimezone(NY) + datetime.timedelta(hours=6)    # journée future : 18:00 NY
            return (d.year, d.month, d.day)
        e = int(t.timestamp() // 60)
        return e // tfm2
    bars = []  # (key, o,h,l,c, last_index)
    for i in range(n):
        k = key(T[i])
        if bars and bars[-1][0] == k:
            b = bars[-1]; bars[-1] = (k, b[1], max(b[2], S['rh'][i]), min(b[3], S['rl'][i]), S['rc'][i], i)
        else:
            bars.append((k, S['ro'][i], S['rh'][i], S['rl'][i], S['rc'][i], i))
    # HA
    ha = []
    for j, b in enumerate(bars):
        hc = (b[1] + b[2] + b[3] + b[4]) / 4
        ho = (b[1] + b[4]) / 2 if j == 0 else (ha[-1][0] + ha[-1][3]) / 2
        ha.append((ho, max(b[2], ho, hc), min(b[3], ho, hc), hc))
    hc = [x[3] for x in ha]; e50 = ema(hc, 50)
    s4 = [sum(x) / 4 for x in ha]; bullh = [a > b for a, b in zip(ema(s4, 4), ema(s4, 32))]
    st = {}
    out = [None] * n
    # une bougie HTF est clôturée à la barre i si la barre i est sa dernière barre (i == last_index)
    # et que la barre suivante change de clé ; on prend donc l'état de la HTF j à partir de last_index(j)
    lastj = -1; jptr = 0
    closed = [None] * n
    for j, b in enumerate(bars):
        if j + 1 < len(bars) or True:
            closed[b[5]] = j
    cur = None
    for i in range(n):
        if closed[i] is not None and (closed[i] + 1 < len(bars)):   # la HTF j est terminée (la suivante existe)
            cur = closed[i]
        if cur is not None and cur >= 50:
            out[i] = dict(trend=hc[cur] > e50[cur], dash=ha[cur][3] > ha[cur][0], heishi=bullh[cur])
    return out
