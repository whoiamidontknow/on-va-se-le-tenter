"""Niveaux de prix connus à la clôture de chaque barre (sans regard vers le futur).

Familles (nom court -> sens) :
  PY / PM / PW   pivots Traditionnels annuel / mensuel / weekly, P, R1-R5, S1-S5,
                 deux bases : HA (= ce qu'affiche CompletV3 : request.security sur le graphique Heiken Ashi,
                 donc h/l/c de la bougie HA de la période) et REEL (pivot standard sur vrais prix) ;
  DB / DS        bords des zones Detector haussières (bull) / baissières (bear), les 3 affichées ;
  AS / LD / US   haut et bas de la dernière session Asie / Londres / US terminée (vrais prix) ;
  MO             Monday High / Low (lundi 00:00 -> mardi 07:30 Paris, vrais prix) ;
  RD             niveaux ronds du Rondator (multiples de 100) ; RF : ronds fins (NQ 50, MES 25).

Contrôle de la base HA : l'API du terminal web donne le pivot annuel 2026 de NQ1! :
P 21675.03, R1 27114.66, S1 16951.06 -> H = 26399.00 (vrai plus haut, au tick), L = 16235.40 et
C = 22390.69 (pas au tick : open et close HA de la bougie annuelle). L'original calcule donc bien ses pivots
sur la bougie HA de la période, comme CompletV3.

Données journalières : fichiers 1D (MESZ2026, NQZ2026) reconstitués en vrais prix (recon.py) ; pour la
série continue MES1! (avr.-juil.), agrégation de ses propres barres 15 min (pas de 1D disponible).
Journée de bourse = date New York + 6 h (18:00 NY -> jour suivant), semaine ISO de cette date.
"""
import os, sys, datetime, math
HERE = os.path.dirname(os.path.abspath(__file__))
STRAT = os.path.abspath(os.path.join(HERE, '..'))
for p in (STRAT, os.path.join(STRAT, 'maemfe'), os.path.join(STRAT, 'stop_detector')):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np
import data, features, recon, build_all          # noqa: E402
import donnees as md                              # noqa: E402

NY = features.NY; PARIS = features.PARIS
PIV_NAMES = ['P', 'R1', 'S1', 'R2', 'S2', 'R3', 'S3', 'R4', 'S4', 'R5', 'S5']


def tdate(t):
    return (t.astimezone(NY) + datetime.timedelta(hours=6)).date()


def pivots_trad(h, l, c):
    p = (h + l + c) / 3
    r1 = 2 * p - l; s1 = 2 * p - h
    r2 = p + (h - l); s2 = p - (h - l)
    r3 = h + 2 * (p - l); s3 = l - 2 * (h - p)
    r4 = r3 + (p - l); s4 = s3 - (h - p)
    r5 = r4 + (p - l); s5 = s4 - (h - p)
    return dict(P=p, R1=r1, S1=s1, R2=r2, S2=s2, R3=r3, S3=s3, R4=r4, S4=s4, R5=r5, S5=s5)


# ------------------------------------------------------------------ journalier en vrais prix
_DAILY = {}


def daily_from_1d(sym):
    """{date: (O,H,L,C)} vrais prix reconstitués depuis le 1D HA du contrat."""
    if sym in _DAILY: return _DAILY[sym]
    D = data.load()
    seg = max(D[(sym, '1D')], key=len)
    bars = [dict(o=r['o'], h=r['h'], l=r['l'], c=r['c']) for r in seg]
    R = recon.reconstruct(bars, tick=0.25, g=2.0)
    out = {}
    for r, x in zip(seg, R):
        out[r['t'].date()] = (x['ro'], x['rh'], x['rl'], x['rc'])
    _DAILY[sym] = out
    return out


def daily_from_intraday(S):
    out = {}
    for i in range(S['n']):
        d = tdate(S['T'][i])
        if d not in out: out[d] = [S['ro'][i], S['rh'][i], S['rl'][i], S['rc'][i]]
        else:
            b = out[d]; b[1] = max(b[1], S['rh'][i]); b[2] = min(b[2], S['rl'][i]); b[3] = S['rc'][i]
    return {k: tuple(v) for k, v in out.items()}


def pkey(d, kind):
    if kind == 'W': return tuple(d.isocalendar()[:2])
    if kind == 'M': return (d.year, d.month)
    return (d.year,)


def period_bars(daily, kind):
    """Liste ordonnée (clé, O, H, L, C, nb jours) des périodes."""
    out = []
    for d in sorted(daily):
        o, h, l, c = daily[d]; k = pkey(d, kind)
        if out and out[-1][0] == k:
            b = out[-1]; out[-1] = (k, b[1], max(b[2], h), min(b[3], l), c, b[5] + 1)
        else:
            out.append((k, o, h, l, c, 1))
    return out


def pivot_sets(daily, kind, min_days):
    """{clé de période p : {'HA': piv, 'REEL': piv}} calculés sur la période PRÉCÉDENTE (complète)."""
    P = period_bars(daily, kind)
    ha = []
    for j, (k, o, h, l, c, nd) in enumerate(P):
        hc = (o + h + l + c) / 4
        ho = (o + c) / 2 if j == 0 else (ha[-1][0] + ha[-1][3]) / 2
        ha.append((ho, max(h, ho, hc), min(l, ho, hc), hc))
    out = {}
    for j in range(1, len(P)):
        k0, o, h, l, c, nd = P[j - 1]
        if nd < min_days: continue
        sets = {'REEL': pivots_trad(h, l, c)}
        if j - 1 >= 2:     # HA : au moins 2 périodes de chauffe (erreur de l'amorce divisée par 4)
            _, hh, hl, hcc = ha[j - 1]
            sets['HA'] = pivots_trad(hh, hl, hcc)
        out[P[j][0]] = sets
    return out


_HYB = {}


def daily_hybrid(sym):
    """1D reconstitué, remplacé jour par jour par l'agrégation des barres intraday COMPLÈTES du même contrat
    (240 -> 60 -> 30 -> 15 : la plus fine l'emporte). Contrôle : la reconstitution 1D seule se trompe de
    30 pts médians (p90 160) sur le close NQ, l'agrégation 15m retrouve le close HA du 1D à quelques points."""
    if sym in _HYB: return _HYB[sym]
    out = dict(daily_from_1d(sym))
    ser = [s for s in build_all.load() if s['sym'] == sym and s['tfm'] in (15, 30, 60, 240)]
    for S in sorted(ser, key=lambda s: -s['tfm']):
        cnt = {}
        for i in range(S['n']):
            d = tdate(S['T'][i]); cnt[d] = cnt.get(d, 0) + 1
        agg = daily_from_intraday(S)
        need = 0.95 * 1380 / S['tfm']
        for d, v in agg.items():
            if cnt[d] >= need: out[d] = v
    _HYB[sym] = out
    return out


def daily_for(S):
    if S['sym'] in ('MES', 'NQZ'):
        return daily_hybrid(S['sym']), True
    return daily_from_intraday(S), False


def build_levels(S, bases=('HA', 'REEL')):
    """S['LV'][i] = liste de (famille, sous-type, prix) connus à la clôture de i."""
    if 'LV' in S: return S
    daily, has1d = daily_for(S)
    piv = {}
    for kind, fam, mind in (('Y', 'PY', 150), ('M', 'PM', 15), ('W', 'PW', 4)):
        piv[kind] = (fam, pivot_sets(daily, kind, mind))
    n = S['n']; rh, rl, rc = S['rh'], S['rl'], S['rc']
    step_f = 50.0 if S['inst'] == 'NQ' else 25.0
    # sessions et Monday en vrais prix
    sess_def = {'AS': (features.TOKYO, 540, 930), 'LD': (features.LONDON, 480, 990), 'US': (NY, 570, 960)}
    SLr = {}
    for k, (tz, a, b) in sess_def.items():
        cur = None; last = None; prev = False; arr = [None] * n
        for i in range(n):
            inS = features.in_sess(S['T'][i], tz, a, b)
            if inS and not prev: cur = [rh[i], rl[i]]
            elif inS and cur: cur[0] = max(cur[0], rh[i]); cur[1] = min(cur[1], rl[i])
            if not inS and prev and cur: last = tuple(cur); cur = None
            arr[i] = last; prev = inS
        SLr[k] = arr
    MHL = [None] * n; cur = None; wk = None; done = None
    for i in range(n):
        d = S['T'][i].astimezone(PARIS); m = d.hour * 60 + d.minute
        inF = d.weekday() == 0 or (d.weekday() == 1 and m < 450)
        if d.weekday() == 0 and (wk is None or wk != d.isocalendar()[:2]):
            wk = d.isocalendar()[:2]; cur = [rh[i], rl[i]]; done = None
        elif inF and cur: cur[0] = max(cur[0], rh[i]); cur[1] = min(cur[1], rl[i])
        if not inF and cur is not None and done is None and wk == d.isocalendar()[:2]: done = tuple(cur)
        if wk != d.isocalendar()[:2]: done = None; cur = None
        MHL[i] = done
    LV = []
    for i in range(n):
        L = []
        d = tdate(S['T'][i])
        for kind in ('Y', 'M', 'W'):
            fam, tab = piv[kind]
            sets = tab.get(pkey(d, kind))
            if sets:
                for b in bases:
                    if b in sets:
                        for nm in PIV_NAMES:
                            L.append((fam + '_' + b, nm, sets[b][nm]))
        if S.get('hasv'):
            for top, btm in S['Zb'][i]:
                L.append(('DB', 'top', top)); L.append(('DB', 'btm', btm))
            for top, btm in S['Zs'][i]:
                L.append(('DS', 'top', top)); L.append(('DS', 'btm', btm))
        for k in ('AS', 'LD', 'US'):
            x = SLr[k][i]
            if x: L.append((k, 'H', x[0])); L.append((k, 'L', x[1]))
        if MHL[i]: L.append(('MO', 'H', MHL[i][0])); L.append(('MO', 'L', MHL[i][1]))
        c0 = math.floor(rc[i] / 100) * 100
        for k in range(-10, 11):
            L.append(('RD', '100', c0 + 100 * k))
        f0 = math.floor(rc[i] / step_f) * step_f
        for k in range(-8, 9):
            v = f0 + step_f * k
            if abs(v / 100 - round(v / 100)) > 1e-9: L.append(('RF', 'fin', v))
        LV.append(L)
    S['LV'] = LV
    return S


def charger(tfs=(15,), avec_sans_volume=True):
    """Séries du cache commun (sans chevauchement) + niveaux. Les séries sans volume (MES1! avr.-juil.)
    n'ont ni Detector ni climax mais servent pour pivots / sessions / Monday / ronds."""
    S_all = md.selectionner(build_all.load(), tfs)
    out = []
    for S in S_all:
        if not S['hasv'] and not avec_sans_volume: continue
        if S['sym'] == 'MES1' and S['n'] < 1500: continue
        S['inst'] = md.instrument(S['sym'])
        build_levels(S)
        out.append(S)
    return out


if __name__ == '__main__':
    # contrôle : journalier 1D reconstitué contre agrégation des barres 15 min (même contrat)
    for S in md.selectionner(build_all.load(), (15,)):
        if S['sym'] not in ('MES', 'NQZ'): continue
        A0 = daily_from_1d(S['sym']); A = daily_hybrid(S['sym']); B = daily_from_intraday(S)
        ks = sorted(set(A) & set(B))[1:-1]
        e = np.array([[A[k][j] - B[k][j] for j in range(4)] for k in ks])
        print(S['sym'], 'jours communs', len(ks), 'écart médian |O H L C|', np.median(np.abs(e), 0).round(2),
              'p90', np.quantile(np.abs(e), .9, 0).round(2))
        for kind, mind in (('W', 4), ('M', 15), ('Y', 150)):
            ps = pivot_sets(A, kind, mind)
            if not ps: print("  ", kind, "aucune période complète"); continue
            last = sorted(ps)[-1]
            print('  ', kind, last, {b: {k: round(v, 1) for k, v in ps[last][b].items() if k in ('P', 'R1', 'S1', 'R2', 'S2')} for b in ps[last]})
        lo, hi = min(S['rl']), max(S['rh'])
        print('   plage 15m', round(lo, 1), round(hi, 1))
