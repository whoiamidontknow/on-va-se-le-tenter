"""Détail par unité / symbole / période, brut et net, pour quelques couples entrée-sortie."""
import sys, build_all, engine as E, strat as T
S_all = [s for s in build_all.load() if s['tfm'] in (5, 15, 30, 60, 240)]
CASES = {'sigF+Heishi': ('sigF', dict(stop=('atr', 1.5), exit_on=T.x_heishi)),
         'sigF+obj2': ('sigF', dict(stop=('atr', 1.5), target=2)),
         'tl+obj2': ('tl', dict(stop=('atr', 1.5), target=2)),
         'tl+Heishi': ('tl', dict(stop=('atr', 1.5), exit_on=T.x_heishi)),
         'detC+obj2': ('det_cassure', dict(stop=('atr', 1.5), target=2)),
         'clx+Heishi': ('clx', dict(stop=('atr', 1.5), exit_on=T.x_heishi)),
         'heishi1+Heishi': ('heishi1', dict(stop=('atr', 1.5), exit_on=T.x_heishi))}
def key(s):
    per = 'avr-jul' if s['T'][0].month < 8 else 'aou-oct'
    return '%s %s %s' % ('MES' if s['sym'] in ('MES', 'MES1') else 'NQ ', s['tf'].rjust(3), per)
for name, (en, kw) in CASES.items():
    print('==', name)
    rows = {}
    for s in S_all:
        k = key(s)
        net = E.run(s, T.ENTRIES[en](s), **kw); brut = E.run(s, T.ENTRIES[en](s), cost=False, **kw)
        r = rows.setdefault(k, [[], []]); r[0] += brut; r[1] += net
    for k in sorted(rows):
        b, n = rows[k]
        sb, sn = E.stats(b), E.stats(n)
        if sn['n'] == 0: continue
        cost = sb['avgR'] - sn['avgR']
        print('  %-18s n=%3d  brut moyR %+.2f  net moyR %+.2f (coût %.2fR)  PF net %.2f  gain %2.0f%%' % (k, sn['n'], sb['avgR'], sn['avgR'], cost, min(sn['pf'], 99), 100 * sn['win']))
