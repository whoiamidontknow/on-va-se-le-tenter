"""Valide la reconstitution des vrais prix DANS un backtest : mêmes signaux (API), exécution sur
vrais prix contre prix reconstitués depuis HA. Si les statistiques concordent, les CSV (HA seuls)
peuvent servir de banc d'essai réaliste."""
import api, engine as E, strat as T
V = {u: api.series(u, 'vrai') for u in ('15m', '2m')}
Rc = {u: api.series(u, 'recon') for u in ('15m', '2m')}
CASES = [('sigF stop1.5ATR obj2R', 'sigF', dict(stop=('atr', 1.5), target=2)),
         ('sigF stop1ATR sortie Heishi', 'sigF', dict(stop=('atr', 1.0), exit_on=T.x_heishi)),
         ('sigF swing5 obj1.5R', 'sigF', dict(stop=('swing', 5), target=1.5)),
         ('sigF trail2ATR', 'sigF', dict(stop=('atr', 2), trail=2.0)),
         ('heishi1 stop1.5 sortie Heishi', 'heishi1', dict(stop=('atr', 1.5), exit_on=T.x_heishi)),
         ('tl stop1.5 obj2', 'tl', dict(stop=('atr', 1.5), target=2)),
         ('clx stop1 obj1', 'clx', dict(stop=('atr', 1.0), target=1)),
         ('sigF 8 barres sans stop', 'sigF', dict(stop=None, max_bars=8))]
for name, en, kw in CASES:
    for u in ('15m', '2m'):
        a = []; b = []; diffs = []
        for Sv, Sr in zip(V[u], Rc[u]):
            ent = T.ENTRIES[en](Sv)
            ta = E.run(Sv, ent, **kw); tb = E.run(Sr, ent, **kw)
            a += ta; b += tb
            m = {t['t']: t['R'] for t in tb}
            diffs += [abs(t['R'] - m[t['t']]) for t in ta if t['t'] in m]
        diffs.sort()
        print('%-30s %s VRAI  %s' % (name, u, E.fmt(E.stats(a))))
        print('%-30s %s RECON %s   |écart R/trade| méd %.2f p90 %.2f' % ('', u, E.fmt(E.stats(b)),
              diffs[len(diffs) // 2] if diffs else 0, diffs[int(.9 * (len(diffs) - 1))] if diffs else 0))
