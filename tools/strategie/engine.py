"""Moteur de backtest sur VRAIS prix (reconstitués depuis HA, ou vrais prix de l'API).

Conventions (prudentes) :
- signal connu à la CLÔTURE de la barre i -> entrée au marché à l'OUVERTURE de i+1, +1 tick contre nous ;
- stop au marché : rempli au stop -1 tick (ou à l'ouverture si elle a sauté le stop) ;
- objectif : ordre limite rempli au prix objectif seulement si le prix le DÉPASSE d'un tick, puis -1 tick ;
- si stop et objectif sont touchés dans la même barre : on prend le STOP ;
- sortie sur signal (flèche/Heishinator opposé) : à l'ouverture suivante, -1 tick ;
- fin de séance : sortie à la clôture de la dernière barre qui commence avant l'heure limite, -1 tick ;
- commission 2,5 $ aller-retour par contrat.
"""
import datetime
from zoneinfo import ZoneInfo
PARIS = ZoneInfo('Europe/Paris'); NY = ZoneInfo('America/New_York')
SPEC = {'MES': (5.0, 0.25), 'MES1': (5.0, 0.25), 'NQZ': (20.0, 0.25), 'API': (20.0, 0.25)}
COMM = 2.5


def sess_of(t):
    d = t.astimezone(PARIS); m = d.hour * 60 + d.minute
    if m < 480: return 'ASIE'
    if m < 870: return 'LONDRES'
    if m < 1320: return 'US'
    return 'SOIR'


def eod_hit(S, j):
    """vrai si la barre j est la dernière qui commence avant 16:00 New York (clôture US)."""
    if S['tfm'] >= 240: return False
    t = S['T'][j].astimezone(NY); m = t.hour * 60 + t.minute
    return m < 960 <= m + S['tfm']


def run(S, entries, stop=('atr', 1.5), target=None, exit_on=None, trail=None, eod=False, max_bars=None,
        sessions=None, filt=None, cost=True, reverse=False, prudent=False):
    """entries : liste triée de (i, dir). exit_on : fonction(S, j, dir) -> True si sortie à la clôture de j."""
    pv, tick = SPEC[S['sym']]
    slip = tick if cost else 0.0
    comm_pts = COMM / pv if cost else 0.0
    ro, rh, rl, rc, atr = S['ro'], S['rh'], S['rl'], S['rc'], S['ratr']
    n = S['n']; trades = []; busy_until = -1
    E = {}
    for i, d in entries:
        E.setdefault(i, d)
    pos = None
    for i in range(n - 1):
        # ---- gestion de la position ouverte sur la barre i
        if pos is not None and i >= pos['j0']:
            d = pos['d']; ex = None
            if i > pos['j0'] and S['brk'][i] and eod:   # sécurité : ne pas traverser une coupure si fin de séance
                ex = (ro[i] - d * slip, 'coupure')
            lo, hi = rl[i], rh[i]
            if prudent and 'rhx' in S:   # côté défavorable : borne la pire ; côté favorable : borne la moins bonne
                lo_adv, hi_adv = S['rlx'][i], S['rhx'][i]
                lo_fav, hi_fav = S['rln'][i], S['rhn'][i]
            else:
                lo_adv, hi_adv, lo_fav, hi_fav = lo, hi, lo, hi
            if ex is None and pos['stop'] is not None:
                if (d == 1 and lo_adv <= pos['stop']) or (d == -1 and hi_adv >= pos['stop']):
                    px = pos['stop'] if i == pos['j0'] else (min(ro[i], pos['stop']) if d == 1 else max(ro[i], pos['stop']))
                    ex = (px - d * slip, 'stop')
            if ex is None and pos['tgt'] is not None:
                if (d == 1 and hi_fav >= pos['tgt'] + tick) or (d == -1 and lo_fav <= pos['tgt'] - tick):
                    ex = (pos['tgt'] - d * slip, 'objectif')
            if ex is None:
                pos['bars'] += 1
                pos['best'] = max(pos['best'], hi_fav) if d == 1 else min(pos['best'], lo_fav)
                if trail is not None and atr[i]:
                    ns = pos['best'] - d * trail * atr[i]
                    if pos['stop'] is None or (d == 1 and ns > pos['stop']) or (d == -1 and ns < pos['stop']):
                        pos['stop'] = ns
                if eod and eod_hit(S, i):
                    ex = (rc[i] - d * slip, 'fin_seance')
                elif exit_on is not None and exit_on(S, i, d):
                    ex = (ro[i + 1] - d * slip, 'signal')
                elif max_bars is not None and pos['bars'] >= max_bars:
                    ex = (ro[i + 1] - d * slip, 'temps')
                elif i + 1 in E and E[i + 1] == -d and False:
                    pass
            if ex is not None:
                px, why = ex
                pnl = d * (px - pos['px']) - comm_pts
                trades.append(dict(sym=S['sym'], tf=S['tf'], t=S['T'][pos['ie']], d=d, entry=pos['px'], exit=px,
                                   risk=pos['risk'], pnl=pnl, R=pnl / pos['risk'], usd=pnl * pv, why=why,
                                   bars=pos['bars'], sess=sess_of(S['T'][pos['ie']])))
                pos = None
        # ---- nouvelle entrée (signal à la clôture de i)
        if pos is None and i in E and i + 1 < n and not S['brk'][i + 1]:
            d = E[i]
            if reverse: d = -d
            if sessions and sess_of(S['T'][i]) not in sessions: continue
            if filt is not None and not filt(S, i, d): continue
            if eod and S['tfm'] < 240:
                t = S['T'][i].astimezone(NY); m = t.hour * 60 + t.minute
                if 960 - S['tfm'] <= m < 1080: continue   # pas d'entrée sur la dernière barre ni après la clôture US
            a = atr[i]
            if not a: continue
            px = ro[i + 1] + d * slip
            if stop is None:
                st = None; risk = a
            elif stop[0] == 'atr':
                st = px - d * stop[1] * a; risk = stop[1] * a
            elif stop[0] == 'swing':   # sous le plus bas des N dernières barres (vrais prix) - 0,1 ATR
                N = stop[1]
                lvl = min(rl[i - N + 1:i + 1]) - 0.1 * a if d == 1 else max(rh[i - N + 1:i + 1]) + 0.1 * a
                risk = d * (px - lvl)
                if risk < 0.5 * a: lvl = px - d * 0.5 * a; risk = 0.5 * a
                if risk > 3 * a: continue
                st = lvl
            tg = px + d * target * risk if target else None
            pos = dict(d=d, px=px, stop=st, tgt=tg, risk=risk, j0=i + 1, ie=i, bars=0, best=px)
    return trades


def stats(tr):
    if not tr: return dict(n=0)
    R = [t['R'] for t in tr]
    w = [r for r in R if r > 0]; lo = [r for r in R if r <= 0]
    eq = 0; pk = 0; dd = 0
    for t in sorted(tr, key=lambda t: t['t']):
        eq += t['R']; pk = max(pk, eq); dd = max(dd, pk - eq)
    usd = [t['usd'] for t in tr]
    return dict(n=len(tr), win=len(w) / len(tr), avgR=sum(R) / len(R), pf=(sum(w) / -sum(lo)) if lo and sum(lo) < 0 else float('inf'),
                ddR=dd, usd=sum(usd) / len(usd), totR=sum(R))


def fmt(s):
    if s['n'] == 0: return 'n=0'
    return 'n=%3d gain %4.0f%% moyR %+.3f PF %4.2f DD %4.1fR totR %+6.1f $/trade %+7.1f' % (
        s['n'], 100 * s['win'], s['avgR'], min(s['pf'], 99), s['ddR'], s['totR'], s['usd'])
