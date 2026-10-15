"""Criblage des ENTRÉES : chaque type d'entrée avec 3 sorties standard, MES (+MES1) contre NQ,
unités 5 à 60 min, vrais prix reconstitués, coûts inclus. Aussi le sens inverse (contre-tendance)."""
import build_all, engine as E, strat as T
S_all = [s for s in build_all.load() if s['tfm'] in (5, 15, 30, 60)]
EXITS = {'stop1.5+obj2R': dict(stop=('atr', 1.5), target=2),
         'stop1.5+Heishi': dict(stop=('atr', 1.5), exit_on=T.x_heishi),
         '8 barres': dict(stop=('atr', 3), max_bars=8)}
def grp(s): return 'MES' if s['sym'] in ('MES', 'MES1') else 'NQ'
for en in T.ENTRIES:
    for rev in (False, True):
        for xn, kw in EXITS.items():
            res = {}
            for s in S_all:
                res.setdefault(grp(s), []).extend(E.run(s, T.ENTRIES[en](s), reverse=rev, **kw))
            print('%-12s %-4s %-15s' % (en, 'INV' if rev else '', xn), ' | '.join('%s %s' % (g, E.fmt(E.stats(res[g]))[:62]) for g in ('MES', 'NQ')))
