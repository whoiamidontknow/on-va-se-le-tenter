"""3. CONTEXTE des déclencheurs : séance, tranche de 30 min (Paris), jour, volatilité relative, TREND 1 et 2 unités
au-dessus. Trades engine (entrée immédiate, sortie du préréglage, coûts inclus). Cases n>=30 seulement ;
p-valeurs (test t de la moyenne de R contre 0) corrigées par Benjamini-Hochberg sur TOUTES les cases testées.
Vérifie « Signator perd à Londres » sur MES avr-jul 15m (autre régime que sep-oct)."""
import numpy as np, pandas as pd
from scipy import stats as st
import conf_common as C
import strat as T

L = C.load()
rows = []
for S in L:
    for trig in ('tl', 'clxL', 'sigF', 'sigFraw', 'sess'):
        if trig == 'sigFraw':
            k, tg, x, f = 1.0, None, T.x_heishi, None; sg = C.trig(S, 'sigF')
        else:
            k, tg, x, f = C.PRESET[trig]; sg = C.trig(S, trig)
        sg = C.apply_filter(S, sg, f)
        for t in C.sim(S, C.fills_immediate(S, sg), stop_k=k, target=tg, exit_on=x):
            i = t['i']; H, H2 = S['htf'][i], S['htf2'][i]
            ar = C.atr_rel(S, i)
            rows.append(dict(trig=trig, set=S['set'], tf=S['tfm'], R=t['R'], d=t['d'], half=1 + (i >= S['n'] // 2),
                             sess=C.session5(t['t']), date=t['t'].astimezone(C.PARIS).date(), sym=S['sym'], slot=C.slot30(t['t']), wd=t['t'].astimezone(C.PARIS).weekday(),
                             atr=ar, tr1=None if H is None else (H['trend'] == (t['d'] == 1)),
                             tr2=None if H2 is None else (H2['trend'] == (t['d'] == 1))))
df = pd.DataFrame(rows)
df['period'] = np.where(df.set == 'MES1', 'avr-jul', np.where(df.set.str.startswith('API'), 'API', 'sep-oct'))
q1, q2 = df.atr.quantile([1 / 3, 2 / 3])
df['vol'] = pd.cut(df.atr, [0, q1, q2, 99], labels=['vol basse', 'vol moyenne', 'vol haute'])
print('seuils ATR relatif (ATR / moyenne 100 barres) : %.2f / %.2f' % (q1, q2))

cells = []


def table(by, trigs, label, min_n=30, periods=('sep-oct', 'avr-jul', 'API', 'tout')):
    print('\n--- %s par %s' % ('+'.join(trigs), label))
    sub = df[df.trig.isin(trigs)]
    for key, g in sub.groupby(by, observed=True):
        out = []
        for p in periods:
            gg = g if p == 'tout' else g[g.period == p]
            R = gg.R.values
            if len(R) < 2: out.append('%-7s n%3d    -   ' % (p, len(R))); continue
            m = R.mean(); tt, pv = st.ttest_1samp(R, 0)
            flag = '' if len(R) >= min_n else '*'
            out.append('%-7s n%3d%s %+.2f t%+.1f' % (p, len(R), flag, m, tt))
            if len(R) >= min_n: cells.append(('+'.join(trigs), label, str(key), p, len(R), m, tt, pv))
        print('  %-22s' % str(key), ' | '.join(out))


for trigs in (['tl'], ['clxL'], ['sigF'], ['sigFraw'], ['sess'], ['tl', 'clxL', 'sigF', 'sess']):
    table('sess', trigs, 'séance')
for trigs in (['tl'], ['sigFraw'], ['tl', 'clxL', 'sigF', 'sess']):
    table('vol', trigs, 'volatilité')
    table('tr1', trigs, 'TREND 1 unité au-dessus aligné')
    table('tr2', trigs, 'TREND 2 unités au-dessus aligné')
    table('wd', trigs, 'jour (0=lundi)')
table('slot', ['tl', 'clxL', 'sigF', 'sess'], 'tranche 30 min Paris (index = heure*2)')

print('\n--- « Signator perd à Londres » : sigF sans filtre, sortie Heishi, stop 1 ATR')
for p in ('sep-oct', 'avr-jul', 'API'):
    g = df[(df.trig == 'sigFraw') & (df.period == p)]
    ld = g[g.sess == 'LONDRES 08-14:30'].R; ot = g[g.sess != 'LONDRES 08-14:30'].R
    if len(ld) > 1 and len(ot) > 1:
        print('  %-8s Londres n%3d moyR %+.2f méd %+.2f | hors Londres n%3d moyR %+.2f méd %+.2f | Mann-Whitney p=%.2f' % (
            p, len(ld), ld.mean(), ld.median(), len(ot), ot.mean(), ot.median(), st.mannwhitneyu(ld, ot).pvalue))
for trig in ('tl', 'sess'):
    for p in ('sep-oct', 'avr-jul', 'API'):
        g = df[(df.trig == trig) & (df.period == p)]
        ld = g[g.sess == 'LONDRES 08-14:30'].R; ot = g[g.sess != 'LONDRES 08-14:30'].R
        if len(ld) > 1 and len(ot) > 1:
            print('  %-4s %-8s Londres n%3d moyR %+.2f | hors Londres n%3d moyR %+.2f | MW p=%.2f' % (
                trig, p, len(ld), ld.mean(), len(ot), ot.mean(), st.mannwhitneyu(ld, ot).pvalue))

cdf = pd.DataFrame(cells, columns=['trig', 'dim', 'case', 'période', 'n', 'moyR', 't', 'p'])
cdf['BH10%'] = C.bh(cdf.p.values, 0.10)
print('\n%d cases testées (n>=30). Retenues par Benjamini-Hochberg (FDR 10 %%) :' % len(cdf))
print(cdf[cdf['BH10%']].to_string(index=False) if cdf['BH10%'].any() else '  AUCUNE')
print('\nCases à |t| >= 2 (non corrigées) :')
print(cdf[cdf.t.abs() >= 2].sort_values('t').to_string(index=False))
