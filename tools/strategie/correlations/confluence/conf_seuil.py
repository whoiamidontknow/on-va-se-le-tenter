"""1bis. SEUIL DE SCORE : entrée quand le score franchit +k (long) / -k (court), exécution aux conventions engine
(ouverture suivante, 1 tick + commission). k choisi sur la MOITIÉ 1 (15m MES+NQ), jugé sur la moitié 2,
sur MES avr-jul (autre régime) et sur l'API 15m (vrais prix)."""
import numpy as np
import conf_common as C

L = C.load(tfs=(15,))


def entries(S, k, side=0):
    s = S['score']; out = []
    for i in range(101, S['n']):
        if side >= 0 and s[i] >= k > s[i - 1]: out.append((i, 1))
        elif side <= 0 and s[i] <= -k < s[i - 1]: out.append((i, -1))
    return out


def x_score(S, j, d):
    return S['score'][j] * d <= 0


EXITS = {'stop1.5 obj2R': dict(stop_k=1.5, target=2), 'stop1.5 sortie score<=0': dict(stop_k=1.5, exit_on=x_score),
         'stop1.5 8 barres': dict(stop_k=1.5, max_bars=8)}


def run(sets, k, side, ex, half=None):
    R = []
    for S in L:
        if S['set'] not in sets: continue
        e = entries(S, k, side)
        if half: e = [(i, d) for i, d in e if (i >= S['n'] // 2) == (half == 2)]
        R += [t['R'] for t in C.sim(S, C.fills_immediate(S, e), **ex)]
    return C.stats_R(R)


for side, sn in ((0, 'long+court'), (1, 'long seul'), (-1, 'court seul')):
    for xn, ex in EXITS.items():
        print('== %s, %s' % (sn, xn))
        best = None
        for k in range(3, 13):
            s1 = run(('MES', 'NQ'), k, side, ex, half=1)
            if s1['n'] >= 30 and (best is None or s1['m'] > best[1]): best = (k, s1['m'])
            s2 = run(('MES', 'NQ'), k, side, ex, half=2)
            s3 = run(('MES1',), k, side, ex); s4 = run(('API15',), k, side, ex)
            print('  k=%2d  moitié1 %s | moitié2 %s | MESavr-jul %s | API15 %s' % (k, C.fmtR(s1), C.fmtR(s2), C.fmtR(s3), C.fmtR(s4)))
        print('  -> k choisi sur moitié 1 (n>=30) :', best)
