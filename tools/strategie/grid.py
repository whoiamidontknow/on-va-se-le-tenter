"""Grille restreinte : entrée x filtre x sortie. Apprentissage = MES (avr-jul + sep-oct),
validation = NQ (CSV, prix reconstitués) puis API Nasdaq 15m (VRAIS prix). Unités 5-60 min."""
import itertools, pickle, build_all, api, engine as E, strat as T
S_csv = [s for s in build_all.load() if s['tfm'] in (5, 15, 30, 60)]
MES = [s for s in S_csv if s['sym'] in ('MES', 'MES1')]; NQ = [s for s in S_csv if s['sym'] == 'NQZ']
A15 = api.series('15m', 'vrai'); A2 = api.series('2m', 'vrai')
ENTR = ['sigF', 'tl', 'det_cassure', 'heishi1', 'clx', 'sess']
FILT = {'aucun': None, 'TREND': T.f_trend, 'TREND2': T.f_trend2, 'Moyen': T.f_moy, 'ADX25': T.f_adx(25),
        'TREND+Moyen': T.f_and(T.f_trend, T.f_moy), 'HeishiHTF': T.f_heishi_htf}
SESS = {'toutes': None, 'LD+US': ('LONDRES', 'US')}
EXIT = {}
for k in (1.0, 1.5, 2.0):
    for tg in (1.5, 2, 3):
        EXIT['stop%.1f obj%sR' % (k, tg)] = dict(stop=('atr', k), target=tg)
    EXIT['stop%.1f Heishi' % k] = dict(stop=('atr', k), exit_on=T.x_heishi)
    EXIT['stop%.1f suiveur%.1f' % (k, k)] = dict(stop=('atr', k), trail=k)
res = []
for en, (fn, f), (sn, ss), (xn, kw) in itertools.product(ENTR, FILT.items(), SESS.items(), EXIT.items()):
    out = {}
    for name, L in (('MES', MES), ('NQ', NQ), ('A15', A15), ('A2', A2)):
        tr = []
        for s in L: tr += E.run(s, T.ENTRIES[en](s), filt=f, sessions=ss, **kw)
        out[name] = E.stats(tr)
    res.append(((en, fn, sn, xn), out))
pickle.dump(res, open('grid_res.pkl', 'wb'))
print(len(res), 'configurations')
