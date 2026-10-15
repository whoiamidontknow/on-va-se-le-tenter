import sys, build_all, api, engine as E, strat as T
S_csv = [s for s in build_all.load() if s['tfm'] in (5, 15, 30, 60)]
A15 = api.series('15m', 'vrai'); A2 = api.series('2m', 'vrai')
SETS = [('MESavr-jul', [s for s in S_csv if s['sym'] == 'MES1' and s['T'][0].month < 8]),
        ('MESsep-oct', [s for s in S_csv if s['sym'] in ('MES', 'MES1') and s['T'][0].month >= 8]),
        ('NQsep-oct', [s for s in S_csv if s['sym'] == 'NQZ']), ('API15', A15), ('API2', A2)]
def show(name, en, kw, longonly=False):
    row = []
    for sn, L in SETS:
        tr = []
        for s in L: tr += E.run(s, T.ENTRIES[en](s) if not longonly else [x for x in T.ENTRIES[en](s) if x[1] == 1], **kw)
        st = E.stats(tr)
        row.append('%s n%3d %+.2f' % (sn, st['n'], st.get('avgR', 0)))
    print('%-34s' % name, ' | '.join(row))
if __name__ == '__main__':
    for th in (0.6, 0.7, 0.8):
        show('feu%.1f stop1.5 Heishi' % th, 'feu', dict(stop=('atr', 1.5), exit_on=T.x_heishi))
        show('sigF +Feu%.1f stop1.5 Heishi' % th, 'sigF', dict(filt=T.f_feu(th), stop=('atr', 1.5), exit_on=T.x_heishi))
        show('tl +Feu%.1f stop1.5 obj2' % th, 'tl', dict(filt=T.f_feu(th), stop=('atr', 1.5), target=2))
        show('clx +Feu%.1f stop2 Heishi' % th, 'clx', dict(filt=T.f_feu(th), stop=('atr', 2), exit_on=T.x_heishi))
        show('detC +Feu%.1f stop2 Heishi' % th, 'det_cassure', dict(filt=T.f_feu(th), stop=('atr', 2), exit_on=T.x_heishi))
    for ses in ('ASIE', 'LONDRES', 'US', 'SOIR'):
        for en, kw in (('sigF', dict(stop=('atr', 1.5), exit_on=T.x_heishi)), ('tl', dict(stop=('atr', 1.5), target=2)),
                       ('clx', dict(stop=('atr', 2), exit_on=T.x_heishi, filt=T.f_trend)), ('base', dict(stop=('atr', 1.5), target=2))):
            show('%s %s' % (en, ses), en, dict(sessions=(ses,), **kw))
