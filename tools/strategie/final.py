"""Chiffres finaux des 3 candidats : par jeu, par unité, en mode prudent, et avec 2 ticks de glissement."""
import build_all, api, engine as E, strat as T
from cands2 import SETS
LONG = lambda S, i, d: d == 1
HORS_LD = ('ASIE', 'US', 'SOIR')
C = {
 'A  Climax BUY long, TREND, stop 2 ATR, sortie Heishi': ('clx', dict(stop=('atr', 2.0), exit_on=T.x_heishi, filt=T.f_and(T.f_trend, LONG))),
 'B  Signator Fort, TREND, hors Londres, stop 1 ATR, sortie Heishi': ('sigF', dict(stop=('atr', 1.0), exit_on=T.x_heishi, filt=T.f_trend, sessions=HORS_LD)),
 'C  Cassure trendline, hors Londres, stop 1.5 ATR, obj 2R': ('tl', dict(stop=('atr', 1.5), target=2, sessions=HORS_LD)),
}
for name, (en, kw) in C.items():
    print('==', name)
    allcsv = []
    for sn, L in SETS:
        tr = []; trp = []; tr2 = []
        for s in L:
            ent = T.ENTRIES[en](s)
            tr += E.run(s, ent, **kw)
            trp += E.run(s, ent, prudent=True, **kw)
        if sn.startswith(('MES', 'NQ')): allcsv += tr
        st = E.stats(tr); sp = E.stats(trp)
        if st['n'] == 0: print('   %-11s n=0' % sn); continue
        print('   %-11s %s | prudent moyR %+.2f' % (sn, E.fmt(st), sp.get('avgR', 0)))
    # par unité (CSV)
    by = {}
    for t in allcsv: by.setdefault(('MES' if t['sym'] != 'NQZ' else 'NQ') + ' ' + t['tf'], []).append(t)
    print('   par unité :', ', '.join('%s n%d %+.2f' % (k, len(v), E.stats(v)['avgR']) for k, v in sorted(by.items())))
