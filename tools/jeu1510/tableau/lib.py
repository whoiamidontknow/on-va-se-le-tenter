#!/usr/bin/env python3
"""Bibliotheque commune : chargement des CSV du 15/10 (graphiques Heiken Ashi,
heure de Paris) et indicateurs facon Pine (ta.*). Pur Python, pas de pandas."""
import csv, glob, os, math

DIR = '/Users/jeremk/Jeu 15:10'

def files():
    out = {}
    for fn in sorted(glob.glob(os.path.join(DIR, '*.csv'))):
        b = os.path.basename(fn)
        sym = 'NQ' if 'NQZ' in b else 'MES'
        tf = b.split(', ')[1].split('_')[0]
        out.setdefault((sym, tf), []).append(fn)
    return out

def load(fn):
    rd = csv.reader(open(fn))
    hdr = next(rd)
    iv = hdr.index('Volume') if 'Volume' in hdr else None
    im = hdr.index('Moyenator 1')
    out = []
    for r in rd:
        try:
            o, h, l, c = map(float, r[1:5])
        except Exception:
            continue
        v = float(r[iv]) if iv is not None and r[iv] not in ('', 'NaN') else 0.0
        m1 = float(r[im]) if r[im] not in ('', 'NaN') else None
        out.append(dict(t=r[0], o=o, h=h, l=l, c=c, v=v, m1=m1))
    return out

def get(sym, tf, k=0):
    return load(files()[(sym, tf)][k])

# ---------------- indicateurs ----------------
def ema(v, n):
    k = 2.0 / (n + 1); out = []; e = None
    for x in v:
        e = x if e is None else x * k + e * (1 - k)
        out.append(e)
    return out

def ema_pine(v, n):
    """ta.ema : amorce par SMA des n premieres valeurs."""
    k = 2.0 / (n + 1); out = []; e = None
    for i, x in enumerate(v):
        if i < n - 1: out.append(None); continue
        if e is None: e = sum(v[:n]) / n
        else: e = x * k + e * (1 - k)
        out.append(e)
    return out

def sma(v, n):
    out = []
    for i in range(len(v)):
        if i < n - 1: out.append(None); continue
        out.append(sum(v[i - n + 1:i + 1]) / n)
    return out

def stdev(v, n):
    out = []
    for i in range(len(v)):
        if i < n - 1: out.append(None); continue
        w = v[i - n + 1:i + 1]; m = sum(w) / n
        out.append(math.sqrt(sum((x - m) ** 2 for x in w) / n))
    return out

def rma(v, n):
    out = []; e = None
    for i, x in enumerate(v):
        if i < n - 1: out.append(None); continue
        if e is None: e = sum(v[:n]) / n
        else: e = (e * (n - 1) + x) / n
        out.append(e)
    return out

def rsi(c, n=14):
    g = [0.0]; ls = [0.0]
    for i in range(1, len(c)):
        d = c[i] - c[i - 1]; g.append(max(d, 0.0)); ls.append(max(-d, 0.0))
    ag, al = rma(g[1:], n), rma(ls[1:], n)
    ag = [None] + ag; al = [None] + al
    return [None if ag[i] is None else (100.0 if al[i] == 0 else 100 - 100 / (1 + ag[i] / al[i])) for i in range(len(c))]

def cci(src, n=30):
    ma = sma(src, n); out = []
    for i in range(len(src)):
        if ma[i] is None: out.append(None); continue
        w = src[i - n + 1:i + 1]
        md = sum(abs(x - ma[i]) for x in w) / n
        out.append(0.0 if md == 0 else (src[i] - ma[i]) / (0.015 * md))
    return out

def tr(h, l, c):
    out = [h[0] - l[0]]
    for i in range(1, len(c)):
        out.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    return out

def atr(h, l, c, n=14):
    return rma(tr(h, l, c), n)

def macd(c, f, s, sig):
    ef, es = ema_pine(c, f), ema_pine(c, s)
    line = [None if ef[i] is None or es[i] is None else ef[i] - es[i] for i in range(len(c))]
    st = next(i for i, x in enumerate(line) if x is not None)
    sg = [None] * st + ema_pine(line[st:], sig)
    return line, sg

def vidya_trend(c, h, l, per=10, mom=20, band=2.0):
    """Trend du tableau principal (Midgar) : VIDYA lisse SMA15 +- ATR200*2."""
    n = len(c); v = None; vs = []
    for i in range(n):
        lo = max(1, i - mom + 1)
        sp = sum(max(c[j] - c[j - 1], 0) for j in range(lo, i + 1)) if i >= 1 else 0
        sn = sum(max(c[j - 1] - c[j], 0) for j in range(lo, i + 1)) if i >= 1 else 0
        cmo = abs(100 * (sp - sn) / max(sp + sn, 1))
        a = 2.0 / (per + 1.0)
        v = a * cmo / 100 * c[i] + (1 - a * cmo / 100) * (v if v is not None else 0.0)
        vs.append(v)
    vid = sma(vs, 15); a200 = atr(h, l, c, 200)
    up = False; out = []
    for i in range(n):
        if vid[i] is None or a200[i] is None or i == 0 or vid[i - 1] is None or a200[i - 1] is None:
            out.append(up); continue
        ub = vid[i] + a200[i] * band; lb = vid[i] - a200[i] * band
        ubp = vid[i - 1] + a200[i - 1] * band; lbp = vid[i - 1] - a200[i - 1] * band
        if c[i] > ub and c[i - 1] <= ubp: up = True
        elif c[i] < lb and c[i - 1] >= lbp: up = False
        out.append(up)
    return out

def supertrend(h, l, c, n=10, mult=3.0):
    a = atr(h, l, c, n)
    dirn = [None] * len(c); fu = fl = None; prev = None
    for i in range(len(c)):
        if a[i] is None: continue
        src = (h[i] + l[i]) / 2
        ub = src + mult * a[i]; lb = src - mult * a[i]
        if fu is None:
            fu, fl = ub, lb; dirn[i] = 1; continue
        fl = lb if (lb > fl or c[i - 1] < fl) else fl
        fu = ub if (ub < fu or c[i - 1] > fu) else fu
        pd = dirn[i - 1] or 1
        d = -1 if (pd == 1 and c[i] < fl) else (1 if (pd == -1 and c[i] > fu) else pd)
        dirn[i] = d
    return dirn

def linreg(c, n, off=0):
    out = []
    for i in range(len(c)):
        if i < n - 1: out.append(None); continue
        y = c[i - n + 1:i + 1]; x = list(range(n))
        mx = sum(x) / n; my = sum(y) / n
        sxy = sum((x[k] - mx) * (y[k] - my) for k in range(n)); sxx = sum((x[k] - mx) ** 2 for k in range(n))
        b = sxy / sxx; a = my - b * mx
        out.append(a + b * (n - 1 - off))
    return out
