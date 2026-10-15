"""Contrôle : le test « la zone retient-elle le prix ? » sur l'API (Nasdaq 15 min), avec les VRAIS prix exacts
puis avec les prix reconstitués depuis le HA (recon.py) : le résultat dépend-il de la reconstitution ?"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import regle, api, features   # noqa: E402

M = 400; PROCHE = 0.25; H = 16
rng = np.random.default_rng(3)
for mode in ('vrai', 'recon'):
    hit = near = 0; hitR = np.zeros(M); nearR = np.zeros(M); n = 0
    for S in api.series('15m', mode):
        seg = [dict(v=x) for x in S['v']]
        Zb, Zs, _, _ = features.detector(S['o'], S['h'], S['l'], S['c'], S['v'], keep=10 ** 9)
        S['ZbF'], S['ZsF'] = Zb, Zs
        rh, rl, rc = map(np.asarray, (S['rh'], S['rl'], S['rc']))
        a = np.array([np.nan if x is None else x for x in S['ratr']])
        I = np.arange(101, S['n'] - H)
        J = I[:, None] + np.arange(1, H + 1)[None, :]
        mae = {1: (rc[I] - rl[J].min(1)) / a[I], -1: (rh[J].max(1) - rc[I]) / a[I]}
        for d in (1, -1):
            for k, i in enumerate(I):
                cand = regle.niveau_detector(S, i, d, tick=1.0)
                if cand is None: continue
                d0 = abs(rc[i] - cand) / a[i]
                if not (0.3 <= d0 <= 4): continue
                n += 1; hit += mae[d][k] >= d0; near += mae[d][k] >= d0 - PROCHE
                dr = mae[d][rng.integers(0, len(I), M)]
                hitR += dr >= d0; nearR += dr >= d0 - PROCHE
    print('%-5s n=%d  hit zone %.1f%% hasard %.1f%% | tenue zone %.1f%% hasard %.1f%%' % (
        mode, n, 100 * hit / n, 100 * hitR.mean() / n, 100 * (1 - hit / near), 100 * (1 - hitR.sum() / nearR.sum())))
