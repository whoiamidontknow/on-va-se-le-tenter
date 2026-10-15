"""1. SCORE DE CONFLUENCE : le rendement futur (vrais prix, en ATR) monte-t-il avec le score ?
   - courbe score -> rendement par jeu (MES sep-oct, NQ sep-oct, MES avr-jul, API 15m/2m), corrélation de rang,
     pente OLS avec erreurs HAC (Newey-West, chevauchement des fenêtres) ;
   - moitié 1 / moitié 2 dans le temps ; pente sur le côté long seul et court seul (la dérive haussière
     fabrique une pente même sans information) ; rendement « démeané » ;
   - score pondéré appris (ridge) sur la 1re moitié / sur MES, validé sur la 2de moitié / sur NQ ;
   - seuil : entrée quand le score franchit k, exécution engine (stop 1,5 ATR, objectif 2R / sortie score<0).
"""
import sys, numpy as np, pandas as pd
from scipy import stats as st
import statsmodels.api as sm
import conf_common as C

H = int(sys.argv[1]) if len(sys.argv) > 1 else 8
L = C.load()


def frame(L):
    rows = []
    for S in L:
        n = S['n']; half = n // 2
        for i in range(n):
            if not S['valid'][i]: continue
            f = S['fwd'][H][i]
            if np.isnan(f): continue
            rows.append(dict(set=S['set'], tf=S['tfm'], sid=id(S), i=i, half=1 + (i >= half), s=S['score'][i], f=f,
                             f1=S['fwd'][1][i], cost=S['cost_atr'][i], **{v: S['V'][i, k] for k, v in enumerate(C.VOTES)}))
    return pd.DataFrame(rows)


df = frame(L)
pd.set_option('display.width', 250)


def hac(y, x, lags):
    X = sm.add_constant(np.asarray(x, float))
    r = sm.OLS(np.asarray(y, float), X).fit(cov_type='HAC', cov_kwds=dict(maxlags=lags))
    return r.params[1], r.tvalues[1]


BINS = [-15, -8.5, -5.5, -2.5, 2.5, 5.5, 8.5, 15]
LAB = ['<=-9', '-8..-6', '-5..-3', '-2..+2', '+3..+5', '+6..+8', '>=+9']
print('Rendement futur %d barres (vrais prix, ATR, brut de coûts) selon le score (14 votes, -14..+14)' % H)
for (name, sub) in [('15m MES', df[(df.set == 'MES') & (df.tf == 15)]), ('15m NQ', df[(df.set == 'NQ') & (df.tf == 15)]),
                    ('15m MES avr-jul', df[(df.set == 'MES1')]), ('API 15m (vrais prix)', df[df.set == 'API15']),
                    ('API 2m (vrais prix)', df[df.set == 'API2']),
                    ('5-60m MES+NQ', df[df.set.isin(['MES', 'NQ'])])]:
    b = pd.cut(sub.s, BINS, labels=LAB)
    g = sub.groupby(b, observed=False).f.agg(['mean', 'count'])
    rho, p = st.spearmanr(sub.s, sub.f)
    sl, t = hac(sub.f, sub.s, H)
    lg = sub[sub.s > 0]; sh = sub[sub.s < 0]
    sl_l, t_l = hac(lg.f, lg.s, H); sl_s, t_s = hac(sh.f, sh.s, H)
    print('%-22s rho %+.3f  pente %+.4f ATR/pt (t HAC %+.2f) | côté long pente %+.4f t %+.2f | côté court %+.4f t %+.2f | moy %+.3f' % (
        name, rho, sl, t, sl_l, t_l, sl_s, t_s, sub.f.mean()))
    print('    ' + '  '.join('%s:%+.2f(n%d)' % (k, r['mean'], r['count']) for k, r in g.iterrows()))
    for hf in (1, 2):
        s2 = sub[sub.half == hf]
        sl, t = hac(s2.f - s2.f.mean(), s2.s, H)
        print('      moitié %d : pente démeanée %+.4f t %+.2f, rho %+.3f, n %d' % (hf, sl, t, st.spearmanr(s2.s, s2.f)[0], len(s2)))

# ---------------------------------------------------------------- votes un par un (information de chaque module)
print('\nInformation de chaque vote (pente HAC du rendement %d barres sur le vote, 15m MES+NQ, moitié 1 / moitié 2 / MES avr-jul)' % H)
m15 = df[df.set.isin(['MES', 'NQ']) & (df.tf == 15)]
for v in C.VOTES:
    out = []
    for s2 in (m15[m15.half == 1], m15[m15.half == 2], df[df.set == 'MES1'], df[df.set == 'API15']):
        if s2[v].std() == 0: out.append('   n/a          '); continue
        sl, t = hac(s2.f, s2[v], H); out.append('%+.3f (t%+.1f)' % (sl, t))
    print('  %-9s' % v, ' | '.join(out))

# ---------------------------------------------------------------- poids appris
from sklearn.linear_model import Ridge


def evalw(train, test, label):
    X = train[C.VOTES].values; y = train.f.values
    m = Ridge(alpha=50.0).fit(X, y)
    w = m.coef_
    pe = test[C.VOTES].values @ w
    rho_w = st.spearmanr(pe, test.f)[0]; rho_e = st.spearmanr(test.s, test.f)[0]
    # décision directionnelle : signe du score (égal) ou de la prédiction SANS constante (pas de pari sur la dérive)
    res = {}
    for nm, sc in (('égal', test.s.values), ('pondéré', pe)):
        q = np.quantile(np.abs(sc), 0.8)
        sel = np.abs(sc) >= q
        net = np.sign(sc[sel]) * test.f.values[sel] - test.cost.values[sel]
        res[nm] = (net.mean(), sel.sum())
    print('%-34s rho test : égal %+.3f / pondéré %+.3f | top 20%% |score| net de coûts : égal %+.3f (n%d) pondéré %+.3f (n%d)' % (
        label, rho_e, rho_w, res['égal'][0], res['égal'][1], res['pondéré'][0], res['pondéré'][1]))
    return w


print('\nScore pondéré (ridge) contre score à poids égaux, hors échantillon')
w1 = evalw(m15[m15.half == 1], m15[m15.half == 2], '15m MES+NQ moitié1 -> moitié2')
w2 = evalw(df[(df.set == 'MES') & (df.tf == 15)], df[(df.set == 'NQ') & (df.tf == 15)], '15m MES -> NQ')
w3 = evalw(m15, df[df.set == 'MES1'], '15m sep-oct -> MES avr-jul')
w4 = evalw(m15, df[df.set == 'API15'], '15m CSV -> API 15m vrais prix')
print('  poids appris (moitié 1) :', ' '.join('%s %+.3f' % (v, x) for v, x in zip(C.VOTES, w1)))
print('  poids appris (MES)      :', ' '.join('%s %+.3f' % (v, x) for v, x in zip(C.VOTES, w2)))
