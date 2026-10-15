"""Sensibilité des 3 candidats aux réglages voisins (pas d'optimisation : on regarde si le résultat tient)."""
from cands2 import show
import strat as T
def long_only(f):
    return T.f_and(f, lambda S, i, d: d == 1)
print('--- A : cassure de trendline')
for k in (1.0, 1.5, 2.0):
    for tg in (1.5, 2, 3):
        show('tl stop%.1f obj%s' % (k, tg), 'tl', dict(stop=('atr', k), target=tg))
    show('tl stop%.1f Heishi' % k, 'tl', dict(stop=('atr', k), exit_on=T.x_heishi))
show('tl stop1.5 obj2 +fin séance', 'tl', dict(stop=('atr', 1.5), target=2, eod=True))
show('tl stop1.5 obj2 +TREND', 'tl', dict(stop=('atr', 1.5), target=2, filt=T.f_trend))
show('tl stop1.5 obj2 +ADX25', 'tl', dict(stop=('atr', 1.5), target=2, filt=T.f_adx(25)))
show('tl stop1.5 obj2 sans Londres', 'tl', dict(stop=('atr', 1.5), target=2, sessions=('ASIE', 'US', 'SOIR')))
show('tl swing5 obj2', 'tl', dict(stop=('swing', 5), target=2))
print('--- B : climax acheteur, long seul, tendance')
for k in (1.0, 1.5, 2.0, 2.5):
    show('clxL TREND stop%.1f Heishi' % k, 'clx', dict(stop=('atr', k), exit_on=T.x_heishi, filt=long_only(T.f_trend)))
    show('clxL TREND stop%.1f obj2' % k, 'clx', dict(stop=('atr', k), target=2, filt=long_only(T.f_trend)))
show('clxL sans filtre stop2 Heishi', 'clx', dict(stop=('atr', 2), exit_on=T.x_heishi, filt=long_only(None) if False else (lambda S, i, d: d == 1)))
show('clxL TREND stop2 suiveur2', 'clx', dict(stop=('atr', 2), trail=2, filt=long_only(T.f_trend)))
show('clxL TREND stop2 Heishi +fin séance', 'clx', dict(stop=('atr', 2), exit_on=T.x_heishi, eod=True, filt=long_only(T.f_trend)))
show('clxL Feu0.6 stop2 Heishi', 'clx', dict(stop=('atr', 2), exit_on=T.x_heishi, filt=long_only(T.f_feu(0.6))))
show('REF baseL TREND stop2 Heishi', 'base_long', dict(stop=('atr', 2), exit_on=T.x_heishi, filt=T.f_trend))
print('--- C : Signator Fort')
for k in (1.0, 1.5, 2.0):
    show('sigF TREND stop%.1f Heishi' % k, 'sigF', dict(stop=('atr', k), exit_on=T.x_heishi, filt=T.f_trend))
    show('sigF TREND stop%.1f Heishi sans Londres' % k, 'sigF', dict(stop=('atr', k), exit_on=T.x_heishi, filt=T.f_trend, sessions=('ASIE', 'US', 'SOIR')))
show('sigF stop1 Heishi', 'sigF', dict(stop=('atr', 1), exit_on=T.x_heishi))
show('sigF TREND stop1 suiveur2', 'sigF', dict(stop=('atr', 1), trail=2, filt=T.f_trend))
show('sigF TREND stop1 flèche opposée', 'sigF', dict(stop=('atr', 1), exit_on=T.x_arrow, filt=T.f_trend))
show('sigF L TREND stop1 Heishi', 'sigF', dict(stop=('atr', 1), exit_on=T.x_heishi, filt=long_only(T.f_trend)))
show('REF base TREND stop1 Heishi', 'base', dict(stop=('atr', 1), exit_on=T.x_heishi, filt=T.f_trend))
