"""Candidats : décomposition long/short, par période, et comparaison à une référence sans signal."""
import build_all, api, engine as E, strat as T
S_csv = [s for s in build_all.load() if s['tfm'] in (5, 15, 30, 60)]
A15 = api.series('15m', 'vrai'); A2 = api.series('2m', 'vrai')
def sets():
    yield 'MES avr-jul', [s for s in S_csv if s['sym'] == 'MES1' and s['T'][0].month < 8]
    yield 'MES sep-oct', [s for s in S_csv if s['sym'] in ('MES', 'MES1') and s['T'][0].month >= 8]
    yield 'NQ  sep-oct', [s for s in S_csv if s['sym'] == 'NQZ']
    yield 'API 15m vrai', A15
    yield 'API 2m  vrai', A2
CANDS = [
    ('clx TREND stop2 Heishi', 'clx', dict(filt=T.f_trend, stop=('atr', 2.0), exit_on=T.x_heishi)),
    ('BASE TREND stop2 Heishi', 'base', dict(filt=T.f_trend, stop=('atr', 2.0), exit_on=T.x_heishi)),
    ('BASE_LONG TREND stop2 Heishi', 'base_long', dict(filt=T.f_trend, stop=('atr', 2.0), exit_on=T.x_heishi)),
    ('sigF TREND stop1 Heishi', 'sigF', dict(filt=T.f_trend, stop=('atr', 1.0), exit_on=T.x_heishi)),
    ('BASE TREND stop1 Heishi', 'base', dict(filt=T.f_trend, stop=('atr', 1.0), exit_on=T.x_heishi)),
    ('detC ADX25 stop2 Heishi', 'det_cassure', dict(filt=T.f_adx(25), stop=('atr', 2.0), exit_on=T.x_heishi)),
    ('BASE ADX25 stop2 Heishi', 'base', dict(filt=T.f_adx(25), stop=('atr', 2.0), exit_on=T.x_heishi)),
    ('tl stop1.5 obj2', 'tl', dict(stop=('atr', 1.5), target=2)),
    ('BASE stop1.5 obj2', 'base', dict(stop=('atr', 1.5), target=2)),
    ('tl TREND stop1.5 obj2', 'tl', dict(filt=T.f_trend, stop=('atr', 1.5), target=2)),
]
for name, en, kw in CANDS:
    print('==', name)
    for sn, L in sets():
        tr = []
        for s in L: tr += E.run(s, T.ENTRIES[en](s), **kw)
        lo = [t for t in tr if t['d'] == 1]; sh = [t for t in tr if t['d'] == -1]
        a, b, c = E.stats(tr), E.stats(lo), E.stats(sh)
        f = lambda s: 'n%4d R%+.2f' % (s['n'], s['avgR']) if s['n'] else 'n   0'
        print('   %-13s tous %s PF %.2f | long %s | short %s' % (sn, f(a), min(a.get('pf', 0), 9.9), f(b), f(c)))
