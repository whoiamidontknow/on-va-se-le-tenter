#!/usr/bin/env python3
"""Etape 5 : Feu de Confluence. Couleurs de cellules LUES sur les captures de
l'original (+1 bleu/bleu clair, -1 rouge, 0 orange/navy), 7 captures avec le
verdict du Feu. On cherche quels 10 des 18 cellules SuperTrader votent (vote =
couleur affichee), sous 2 formules :
  F1 : SHORT si nS/29 >= 60 %, LONG si nL/29 >= 60 %, sinon NEUTRE
  F2 : meme chose mais part = n / (nL + nS) (voix neutres exclues)
Variante D : les 6 voix Dashator sont-elles celles AFFICHEES, ou exclues ?"""
import itertools

ST = ['Trend', 'BullSc', 'BearSc', 'YoYo', 'GapUp', 'GapDn', 'Div', 'Cross', 'CCI', 'RSI',
      'MACD', 'PA1', 'PA2', 'PA3', 'VIX', 'VixVol', 'Vol1', 'Vol2']
B, R, N = 1, -1, 0
CAPS = {
 # nom : (supertrader 18, dashator 6, trend 6, signal 7, feu)
 '15/10 9 Normal':  ([R,B,R,B,R,B,B,N,R,R,B,R,N,N,B,B,B,B], [B]*6,             [B,R,R,R,R,B], [R,R,R,B,R,N,R], 'NEUTRE'),
 '15/10 10 Groupe': ([R,B,R,B,R,B,B,N,R,R,B,N,N,N,B,B,B,B], [B,B,B,R,R,R],     [B,R,R,R,R,B], [R,R,R,B,R,N,R], 'NEUTRE'),
 '15/10 11 Groupe': ([R,B,R,B,R,B,B,N,R,R,B,R,N,N,B,B,B,B], [R]*6,             [B,R,R,R,R,B], [R,R,R,B,R,N,R], 'SHORT'),
 '15/10 12 Normal': ([R,B,R,B,R,B,B,N,R,R,B,R,N,N,B,B,B,B], [R]*6,             [B,R,R,R,R,B], [R,R,R,B,R,N,R], 'SHORT'),
 '14/10 7 Normal':  ([R,B,R,B,R,B,N,N,R,R,R,B,R,R,B,B,B,B], [B]*6,             [R,R,R,R,R,B], [R,R,R,B,R,N,N], 'SHORT'),
 '12/10 7 Normal':  ([R,B,R,B,R,B,N,N,R,R,R,N,N,R,B,B,B,B], [R]*6,             [R,R,R,B,B,B], [R,R,R,B,B,N,N], 'NEUTRE'),
 '12/10 8 Groupe':  ([R,B,R,B,R,B,N,N,R,R,B,B,N,R,B,B,B,B], [B,B,B,B,R,B],     [R,R,R,B,B,B], [R,R,R,B,B,N,N], 'NEUTRE'),
}

def verdict(L, S, F):
    den = 29 if F == 'F1' else max(L + S, 1)
    return 'LONG' if L / den >= 0.6 else 'SHORT' if S / den >= 0.6 else 'NEUTRE'

for F in ('F1', 'F2'):
    for D in ('affiche', 'exclu'):
        sols = []
        for sub in itertools.combinations(range(18), 10):
            good = 0
            for name, (st, da, tr, sg, feu) in CAPS.items():
                v = [st[k] for k in sub] + tr + sg + (da if D == 'affiche' else [])
                L = sum(1 for x in v if x == 1); S = sum(1 for x in v if x == -1)
                good += verdict(L, S, F) == feu
            sols.append((good, sub))
        best = max(g for g, _ in sols)
        nb = [s for g, s in sols if g == best]
        print('%s / Dashator %-8s : meilleur %d/7 captures, %d sous-ensembles' % (F, D, best, len(nb)))
        if best == 7:
            # cellules toujours / jamais presentes dans les solutions
            alw = [ST[k] for k in range(18) if all(k in s for s in nb)]
            nev = [ST[k] for k in range(18) if all(k not in s for s in nb)]
            print('     toujours :', alw, '\n     jamais   :', nev)

# Quelle capture bloque ? Pour chaque capture, nombre de sous-ensembles qui satisfont
# toutes les AUTRES captures mais pas elle.
print('\n--- capture bloquante (F1, Dashator affiche) ---')
names = list(CAPS)
for drop in names:
    n = 0
    for sub in itertools.combinations(range(18), 10):
        ok = True
        for name, (st, da, tr, sg, feu) in CAPS.items():
            if name == drop: continue
            v = [st[k] for k in sub] + tr + sg + da
            if verdict(sum(1 for x in v if x == 1), sum(1 for x in v if x == -1), 'F1') != feu: ok = False; break
        n += ok
    print('  sans %-16s : %5d sous-ensembles satisfont les 6 autres' % (drop, n))
# Bilan 14/10 : voix connues hors SuperTrader
st, da, tr, sg, feu = CAPS['14/10 7 Normal']
v = tr + sg + da
print('\n14/10 : hors SuperTrader L=%d S=%d ; cellules SuperTrader rouges affichees = %d (il en faut >= %d sur 10 pour SHORT en F1)'
      % (sum(1 for x in v if x == 1), sum(1 for x in v if x == -1), sum(1 for x in st if x == -1), 18 - sum(1 for x in v if x == -1)))
