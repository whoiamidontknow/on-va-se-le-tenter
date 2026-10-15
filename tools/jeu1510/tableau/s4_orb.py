#!/usr/bin/env python3
"""Etape 4 : ORB 15min. L'original affiche 'In Range' sur les 4 jours releves.
Pour chaque jour, prix de la capture (cloture HA retrouvee a l'etape 1) contre la
plage des 15 premieres minutes selon plusieurs ancres (heure de Paris), calculee
sur les bougies HA de l'unite du graphique ET en 5m (plus fin)."""
from lib import *

L12 = '/Users/jeremk/Ephore/Lun12:10/'
CAPS = [
    # jour, symbole, unite graphique, fichier(s), cloture HA a la capture, heure capture
    ('2026-10-12', 'MES', '15', L12 + 'CME_MINI_MESZ2026, 15_7f431.csv', L12 + 'CME_MINI_MESZ2026, 5_2eb65.csv', None, '14:11'),
    ('2026-10-13', 'NQ', '15', None, None, 30739.375, '10:20'),
    ('2026-10-14', 'NQ', '5', None, None, 30792.5, '11:55'),
    ('2026-10-15', 'NQ', '15', None, None, 29848.625, '11:54'),
]
ANCRES = ['00:00', '01:00', '08:00', '09:00', '15:30']

def rng(b, day, hh, mins=15):
    t0 = day + 'T' + hh
    sel = [x for x in b if x['t'][:16] >= t0 and x['t'][:16] < day + 'T' + '%02d:%02d' % divmod(int(hh[:2]) * 60 + int(hh[3:]) + mins, 60)]
    if not sel: return None
    return max(x['h'] for x in sel), min(x['l'] for x in sel)

def prev_day(day):
    import datetime
    d = datetime.date.fromisoformat(day)
    d -= datetime.timedelta(days=3 if d.weekday() == 0 else 1)
    return d.isoformat()

for day, sym, tf, f1, f5, px, hh in CAPS:
    bt = load(f1) if f1 else get(sym, tf)
    b5 = load(f5) if f5 else get(sym, '5')
    if px is None:
        px = [x for x in bt if x['t'][:16] <= day + 'T' + hh][-1]['c']
    print('== %s %s %sm capture %s, cloture HA %.2f' % (day, sym, tf, hh, px))
    for a in ANCRES:
        for lab, b in (('TF graphique', bt), ('5m', b5)):
            formed = (day + 'T' + a) <= (day + 'T' + hh)
            d = day if formed else prev_day(day)
            r = rng(b, d, a)
            if r is None:
                print('   ancre %s (%s) : pas de donnees' % (a, lab)); continue
            st = 'Above' if px > r[0] else 'Below' if px < r[1] else 'In Range'
            print('   ancre %s %-12s plage %s %.2f-%.2f -> %-8s%s' % (a, lab, d, r[1], r[0], st, '' if formed else '   (ORB du jour PAS ENCORE FORME : plage de la veille)'))
