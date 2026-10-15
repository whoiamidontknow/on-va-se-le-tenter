"""Briques communes : votes des modules, score de confluence, rendements futurs aux vrais prix (en ATR),
simulateur d'entrées décalées (repli / confirmation) aux conventions EXACTES de engine.py, contextes."""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
import numpy as np
import engine as E, features, strat as T
import conf_build as B
from zoneinfo import ZoneInfo
PARIS = ZoneInfo('Europe/Paris')

VOTES = ['heishi', 'moyen', 'trend0', 'trend1', 'trend2', 'dash', 'signator', 'tl', 'sessions', 'monday',
         'detector', 'climax', 'rsi', 'macd']


def load(sets=None, tfs=None):
    L = [S for S in B.load() if not (S['sym'] == 'MES1' and S['set'] == 'MES')]   # doublon MES sep-oct sans volume
    if sets: L = [S for S in L if S['set'] in sets]
    if tfs: L = [S for S in L if S['tfm'] in tfs]
    for S in L: votes(S)
    return L


def _recent(ev, i, k):
    """direction du dernier événement non nul dans les k dernières barres (i compris)."""
    for j in range(i, max(i - k, -1), -1):
        if ev[j]: return ev[j]
    return 0


def votes(S, k_sig=6, k_ev=10):
    if 'V' in S: return S
    n = S['n']; c, o = S['c'], S['o']
    sigd = [0] * n
    for i in range(n):
        x = S['sig'][i]
        if x: sigd[i] = x[1]
    tld = [1 if S['rB'][i] else (-1 if S['sB'][i] else 0) for i in range(n)]
    detd = [1 if S['mitS'][i] else (-1 if S['mitB'][i] else 0) for i in range(n)]
    V = np.zeros((n, len(VOTES)))
    for i in range(1, n):
        H, H2 = S['htf'][i], S['htf2'][i]
        m50, m60 = S['e50'][i], S['e60'][i]
        sv = 0
        for k in ('AS', 'LD', 'US'):
            lv = S['SL'][k][i]
            if lv: sv += (c[i] > lv[0]) - (c[i] < lv[1])
        mh = S['MHL'][i]
        row = [1 if S['bull'][i] else -1,
               1 if c[i] > max(m50, m60) else (-1 if c[i] < min(m50, m60) else 0),
               1 if c[i - 1] > S['e50'][i - 1] else -1,
               0 if H is None else (1 if H['trend'] else -1),
               0 if H2 is None else (1 if H2['trend'] else -1),
               0 if H is None else (1 if H['dash'] else -1),
               _recent(sigd, i, k_sig), _recent(tld, i, k_ev),
               int(np.sign(sv)),
               0 if mh is None else (1 if c[i] > mh[0] else (-1 if c[i] < mh[1] else 0)),
               _recent(detd, i, k_ev), _recent(S['clx'], i, k_ev),
               0 if S['rsi'][i] is None else (1 if S['rsi'][i] > 50 else -1),
               1 if S['macd'][i] > S['macds'][i] else -1]
        V[i] = row
    S['V'] = V; S['score'] = V.sum(1)
    # rendements futurs aux vrais prix, en ATR (entrée ouverture i+1, sortie clôture i+h), sans traverser de coupure
    ro, rc, a = np.array(S['ro']), np.array(S['rc']), np.array([x or np.nan for x in S['ratr']], float)
    brk = np.array(S['brk'])
    cb = np.cumsum(brk)
    S['fwd'] = {}
    for h in (1, 4, 8, 16):
        f = np.full(n, np.nan)
        for i in range(n - h):
            if cb[i + h] != cb[i]: continue
            f[i] = (rc[i + h] - ro[i + 1]) / a[i]
        S['fwd'][h] = f
    pv, tick = E.SPEC[S['sym']]
    S['cost_atr'] = (2 * tick + E.COMM / pv) / a       # aller-retour : 2 ticks + commission, en ATR
    S['valid'] = np.array([i > 100 and not np.isnan(a[i]) for i in range(n)])
    return S


# ------------------------------------------------------------------ contexte
def slot30(t):
    d = t.astimezone(PARIS); return d.hour * 2 + d.minute // 30


def session5(t):
    d = t.astimezone(PARIS); m = d.hour * 60 + d.minute
    if m < 480: return 'ASIE 00-08'
    if m < 870: return 'LONDRES 08-14:30'
    if m < 1050: return 'CHEVAUCH 14:30-17:30'
    if m < 1320: return 'US 17:30-22'
    return 'SOIR 22-24'


def atr_rel(S, i, k=100):
    a = S['ratr']
    w = [x for x in a[max(0, i - k):i] if x]
    return a[i] / (sum(w) / len(w)) if w and a[i] else None


# ------------------------------------------------------------------ simulateur (conventions de engine.run)
def sim(S, fills, stop_k=1.5, target=None, exit_on=None, max_bars=None, prudent=False, cut=False):
    """fills : liste triée de (j, d, px, a, i_sig, kind) : entrée exécutée PENDANT la barre j au prix px
    (glissement déjà inclus), risque = stop_k * a. kind='mkt' (à l'ouverture de j) ou 'lmt' (en cours de barre :
    sur la barre j, on ne prend pas l'objectif, on prend le stop s'il est touché).
    Gestion identique à engine.run (stop prioritaire, objectif +1 tick, sortie signal à l'ouverture suivante)."""
    pv, tick = E.SPEC[S['sym']]; slip = tick; comm = E.COMM / pv
    ro, rh, rl, rc = S['ro'], S['rh'], S['rl'], S['rc']
    n = S['n']; out = []; busy = -1
    for (j, d, px, a, isig, kind) in fills:
        if j <= busy or j >= n - 1: continue
        risk = stop_k * a; st = px - d * risk; tg = px + d * target * risk if target else None
        bars = 0; ex = None; k = j
        while k < n - 1:
            if cut and k > j and S['brk'][k]: ex = (ro[k] - d * slip, 'coupure'); break
            lo_adv, hi_adv, lo_fav, hi_fav = (S['rlx'][k], S['rhx'][k], S['rln'][k], S['rhn'][k]) if prudent else (rl[k], rh[k], rl[k], rh[k])
            if (d == 1 and lo_adv <= st) or (d == -1 and hi_adv >= st):
                p = st if k == j else (min(ro[k], st) if d == 1 else max(ro[k], st))
                ex = (p - d * slip, 'stop'); break
            if tg is not None and not (kind == 'lmt' and k == j):
                if (d == 1 and hi_fav >= tg + tick) or (d == -1 and lo_fav <= tg - tick):
                    ex = (tg - d * slip, 'objectif'); break
            bars += 1
            if exit_on is not None and exit_on(S, k, d): ex = (ro[k + 1] - d * slip, 'signal'); break
            if max_bars is not None and bars >= max_bars: ex = (ro[k + 1] - d * slip, 'temps'); break
            k += 1
        if ex is None: break
        pnl = d * (ex[0] - px) - comm
        out.append(dict(sym=S['sym'], tf=S['tf'], set=S['set'], t=S['T'][isig], i=isig, j=j, d=d, R=pnl / risk,
                        usd=pnl * pv, why=ex[1], bars=bars, half=None))
        busy = k
    return out


def fills_immediate(S, sigs):
    pv, tick = E.SPEC[S['sym']]
    return [(i + 1, d, S['ro'][i + 1] + d * tick, S['ratr'][i], i, 'mkt') for i, d in sigs
            if i + 1 < S['n'] and not S['brk'][i + 1] and S['ratr'][i]]


def fills_confirm(S, sigs, real=False):
    """attend que la bougie i+1 soit de la couleur du sens (HA, ou vraie bougie si real) ; entrée ouverture i+2."""
    pv, tick = E.SPEC[S['sym']]; out = []
    for i, d in sigs:
        j = i + 1
        if j + 1 >= S['n'] or S['brk'][j] or S['brk'][j + 1] or not S['ratr'][i]: continue
        up = (S['rc'][j] > S['ro'][j]) if real else (S['c'][j] > S['o'][j])
        if up == (d == 1):
            out.append((j + 1, d, S['ro'][j + 1] + d * tick, S['ratr'][i], i, 'mkt'))
    return out


def fills_limit(S, sigs, level_fn, N=8, prudent=False):
    """ordre limite renouvelé à chaque barre au niveau level_fn(S, i, d, j) (connu à la clôture de j-1),
    valable N barres après le signal. Rempli si le vrai prix le traverse d'un tick ; prix = niveau (ou
    ouverture si elle est déjà au-delà) + 1 tick de glissement contre nous."""
    pv, tick = E.SPEC[S['sym']]; out = []
    for i, d in sigs:
        if not S['ratr'][i]: continue
        for j in range(i + 1, min(i + 1 + N, S['n'] - 1)):
            if S['brk'][j]: break
            lv = level_fn(S, i, d, j)
            if lv is None: continue
            if (d == 1 and lv >= S['rc'][i]) or (d == -1 and lv <= S['rc'][i]):
                lv = None   # niveau du mauvais côté : ce serait un ordre stop, pas un repli
                continue
            lo_j, hi_j = (S['rln'][j], S['rhn'][j]) if prudent else (S['rl'][j], S['rh'][j])
            if d == 1 and lo_j <= lv - tick:
                out.append((j, d, min(lv, S['ro'][j]) + tick, S['ratr'][i], i, 'lmt')); break
            if d == -1 and hi_j >= lv + tick:
                out.append((j, d, max(lv, S['ro'][j]) - tick, S['ratr'][i], i, 'lmt')); break
    return out


# niveaux de repli
def lv_ema50(S, i, d, j): return S['re50'][j - 1]
def lv_half_atr(S, i, d, j): return S['rc'][i] - d * 0.5 * S['ratr'][i]
def lv_mid_bar(S, i, d, j): return (S['rh'][i] + S['rl'][i]) / 2
def lv_tl(S, i, d, j):
    g = S['tlg'][i]
    return None if g is None else B.tl_value(g, j)


def stats_R(R):
    R = np.asarray(R, float)
    if len(R) == 0: return dict(n=0, m=np.nan, t=np.nan, pf=np.nan)
    w = R[R > 0].sum(); l = -R[R <= 0].sum()
    sd = R.std(ddof=1) if len(R) > 1 else np.nan
    return dict(n=len(R), m=R.mean(), t=R.mean() / sd * math.sqrt(len(R)) if sd and sd > 0 else np.nan,
                pf=w / l if l > 0 else np.inf, win=(R > 0).mean())


def fmtR(s):
    if s['n'] == 0: return 'n=0'
    return 'n%4d moyR %+.3f t %+.2f PF %.2f' % (s['n'], s['m'], s['t'], min(s['pf'], 99))


def bh(pvals, q=0.10):
    """Benjamini-Hochberg : renvoie le masque des tests retenus au taux de fausses découvertes q."""
    p = np.asarray(pvals); m = len(p); o = np.argsort(p); ok = np.zeros(m, bool)
    thr = q * np.arange(1, m + 1) / m
    below = p[o] <= thr
    if below.any():
        k = np.max(np.where(below)[0]); ok[o[:k + 1]] = True
    return ok


# déclencheurs + filtres des 3 préréglages (strat.py / final.py)
def trig(S, name):
    if name == 'tl': return T.e_tl(S)
    if name == 'clxL': return [(i, d) for i, d in T.e_clx(S) if d == 1]
    if name == 'sigF': return T.e_sigF(S)
    if name == 'sess': return T.e_sess(S)
    raise KeyError(name)


PRESET = {  # (stop ATR, objectif R, sortie signal, filtre au signal)
    'tl': (1.5, 2, None, None),
    'clxL': (2.0, None, T.x_heishi, T.f_trend),
    'sigF': (1.0, None, T.x_heishi, T.f_trend),
    'sess': (1.5, 2, None, None),
}


def apply_filter(S, sigs, f):
    return sigs if f is None else [(i, d) for i, d in sigs if f(S, i, d)]
