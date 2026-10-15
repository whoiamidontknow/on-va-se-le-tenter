"""Contrôle des effets de contexte retenus : t « grappé par jour » (les trades d'un même jour, des 4 unités,
de MES et NQ ne sont pas indépendants : on moyenne R par jour puis test t sur les jours) et 15m seul."""
import io, contextlib, numpy as np
from scipy import stats as st
with contextlib.redirect_stdout(io.StringIO()):
    import conf_context as X
df = X.df


def show(lbl, g):
    if len(g) < 2: print('  %-58s n<2' % lbl); return
    d = g.groupby('date').R.mean()
    t15 = g[g.tf == 15].R
    print('  %-58s trades n%3d moy %+.2f | jours n%3d moy %+.2f t_jour %+.2f | 15m seul n%3d moy %+.2f' % (
        lbl, len(g), g.R.mean(), len(d), d.mean(), st.ttest_1samp(d, 0)[0] if len(d) > 1 else np.nan, len(t15),
        t15.mean() if len(t15) else np.nan))


for p in ('sep-oct', 'avr-jul', 'API'):
    print('==', p)
    P = df[df.period == p]
    for trig in ('sigFraw', 'sigF', 'tl', 'clxL', 'sess'):
        g = P[P.trig == trig]
        show('%s Londres' % trig, g[g.sess == 'LONDRES 08-14:30'])
        show('%s hors Londres' % trig, g[g.sess != 'LONDRES 08-14:30'])
    A = P[P.trig.isin(['tl', 'clxL', 'sigF', 'sess'])]
    show('4 déclencheurs mardi', A[A.wd == 1]); show('4 déclencheurs lundi', A[A.wd == 0])
    show('4 déclencheurs autres jours', A[~A.wd.isin([0, 1])])
    show('sigFraw vol basse', P[(P.trig == 'sigFraw') & (P.vol == 'vol basse')])
    show('sigFraw vol moy+haute', P[(P.trig == 'sigFraw') & (P.vol != 'vol basse')])
    show('tl contre TREND HTF', P[(P.trig == 'tl') & (P.tr1 == False)])
    show('tl avec TREND HTF', P[(P.trig == 'tl') & (P.tr1 == True)])
    show('tl hors Londres, contre TREND HTF', P[(P.trig == 'tl') & (P.tr1 == False) & (P.sess != 'LONDRES 08-14:30')])
    show('tl long seul', P[(P.trig == 'tl') & (P.d == 1)]); show('tl court seul', P[(P.trig == 'tl') & (P.d == -1)])
