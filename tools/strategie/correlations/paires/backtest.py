"""Les 5 meilleures règles de l'APPRENTISSAGE (MES 1re moitié, classement par t groupé, G >= 10 jours,
n >= 30, doublons retirés) passées dans engine.run (coûts : 1 tick d'entrée + 1 tick de sortie + 2,5 $),
puis lues HORS échantillon. Aucune règle n'est choisie sur la validation."""
import os, sys, datetime, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import analyse, defs, engine as E

df, S = analyse.prep()


def state(k):
    return np.asarray(defs.DIR[k](df), float)


def lab(k, d):
    return defs.dir_label(defs.DIR[k](df), d)


ENT = defs.entries(df)
NDIR = None


def nd(name, d):
    return np.asarray(defs.nondir(df, d)[name], dtype=object)


def r1():   # rebond Detector dans les 2 barres qui suivent un changement Heishinator
    d = ENT['detR']; return np.where((d != 0) & (nd('age_heishi', d) == '1-2'), d, 0)


def r2():   # sens de la bougie HA 4H clôturée, prix de l'autre côté du range de Londres
    d = np.nan_to_num(np.sign(state('dash_240'))); return np.where((d != 0) & (lab('sess_LD', d) == 'contre'), d, 0)


def r3():   # pendant l'Asie, dans le sens de la sortie du range US précédent
    d = np.nan_to_num(np.sign(state('sess_US'))); return np.where((d != 0) & (df.sess.values == 'ASIE'), d, 0)


def r4():   # sens de la bande Moyenator, prix de l'autre côté du range Asie
    d = np.nan_to_num(np.sign(state('moy_band'))); return np.where((d != 0) & (lab('sess_AS', d) == 'contre'), d, 0)


def r5():   # rebond Detector avec ADX 25-35
    d = ENT['detR']; return np.where((d != 0) & (nd('adx', d) == '25-35'), d, 0)


RULES = {'R1 rebond Detector, Heishi age 1-2': r1, 'R2 bougie 4H HA, prix contre range Londres': r2,
         'R3 Asie, sortie du range US': r3, 'R4 bande Moyenator, prix contre range Asie': r4,
         'R5 rebond Detector, ADX 25-35': r5}
EXITS = {'8 barres (stop 3 ATR)': dict(stop=('atr', 3.0), max_bars=8),
         'stop 1 ATR / obj 1R': dict(stop=('atr', 1.0), target=1)}
setof = {}
for k, m in defs.sets(df).items():
    for sid, day in zip(df.sid[m], df.day[m]): setof[(sid, day)] = k


def run(rule, kw):
    d = rule(); res = {}
    for sid, g in df.assign(_d=d)[d != 0].groupby('sid'):
        s = S[sid]; ent = sorted(zip(g.i.values.tolist(), g._d.astype(int).values.tolist()))
        for t in E.run(s, ent, **kw):
            day = (t['t'].astimezone(E.NY) + datetime.timedelta(hours=6)).date()
            k = setof.get((sid, day))
            if k: t['atr_units'] = t['R'] * kw['stop'][1]; res.setdefault(k, []).append(t)
    return res


if __name__ == '__main__':
    order = defs.SETS_MAIN + defs.SETS_X
    for rn, rf in RULES.items():
        for xn, kw in EXITS.items():
            res = run(rf, kw)
            print('== %s | %s' % (rn, xn))
            for k in order:
                tr = res.get(k, [])
                if not tr: print('   %-13s n=0' % k); continue
                st = E.stats(tr); a = np.mean([t['atr_units'] for t in tr])
                lo = [t for t in tr if t['d'] == 1]; sh = [t for t in tr if t['d'] == -1]
                print('   %-13s %s | ATR/trade %+.2f | long n%d %+.2f short n%d %+.2f' % (
                    k, E.fmt(st), a, len(lo), E.stats(lo).get('avgR', 0), len(sh), E.stats(sh).get('avgR', 0)))
