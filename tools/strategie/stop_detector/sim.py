"""Simulation d'un trade isolé avec une distance de stop donnée — conventions de ../engine.py :
entrée à l'ouverture (vraie) de i+1 + 1 tick ; stop rempli au stop (ou à l'ouverture si elle l'a sauté) - 1 tick ;
objectif rempli seulement si dépassé d'un tick, - 1 tick ; stop ET objectif même barre -> stop ;
sortie Heishinator : changement de couleur à la clôture de j -> ouverture de j+1 - 1 tick ;
commission 1,25 $/contrat/côté. Fin des données : sortie à la dernière clôture.
`sequentiel` reproduit engine.run (une position à la fois) pour contrôle.
"""
import numpy as np
import regle
from donnees import SPEC

COMM_COTE = 1.25


def trade(S, i, d, dist, cible=2.0, sortie='cible', hmax=None):
    """Un trade isolé. sortie : 'cible' (objectif cible x R + stop) ou 'heishi' (changement Heishinator + stop).
    Renvoie dict (pts net, R, usd, why, nb barres) ou None si pas d'entrée possible."""
    pv, tick = SPEC[S['inst']]
    n = S['n']
    if i + 1 >= n or S['brk'][i + 1] or not dist or dist <= 0: return None
    ro, rh, rl, rc, bull = S['ro'], S['rh'], S['rl'], S['rc'], S['bull']
    px = ro[i + 1] + d * tick
    st = px - d * dist
    tg = px + d * cible * dist if sortie == 'cible' else None
    j0 = i + 1; ex = None; why = None; j = j0
    last = n - 1 if hmax is None else min(n - 1, j0 + hmax - 1)
    for j in range(j0, last + 1):
        if (d == 1 and rl[j] <= st) or (d == -1 and rh[j] >= st):
            f = st if j == j0 else (min(ro[j], st) if d == 1 else max(ro[j], st))
            ex, why = f - d * tick, 'stop'; break
        if tg is not None and ((d == 1 and rh[j] >= tg + tick) or (d == -1 and rl[j] <= tg - tick)):
            ex, why = tg - d * tick, 'objectif'; break
        if sortie == 'heishi' and bull[j] != (d == 1) and j + 1 < n:
            ex, why = ro[j + 1] - d * tick, 'signal'; break
    if ex is None:
        ex, why = rc[j], 'fin'
    pnl = d * (ex - px) - 2 * COMM_COTE / pv
    return dict(pts=pnl, R=pnl / dist, usd=pnl * pv, why=why, nb=j - j0 + 1, px=px, stop=st, j_out=j)


def sequentiel(S, entries, k=1.5, cible=2.0):
    """Une position à la fois (comme engine.run, stop ATR x k, objectif cible R) — pour le contrôle."""
    out = []; libre = -1
    for i, d in sorted(entries):
        if i < libre: continue
        a = S['ratr'][i]
        if not a: continue
        t = trade(S, i, d, k * a, cible, 'cible')
        if t is None: continue
        out.append((i, d, t)); libre = t['j_out']
    return out


def sequentiel_gen(S, entries, distfn, cible=2.0, sortie='cible'):
    """Une position à la fois, distance de stop donnée par distfn(S, i, d) -> (dist, zone_utilisee)."""
    out = []; libre = -1
    for i, d in sorted(entries):
        if i < libre: continue
        if not S['ratr'][i]: continue
        dist, z = distfn(S, i, d)
        t = trade(S, i, d, dist, cible, sortie)
        if t is None: continue
        t['zone'] = z
        out.append((i, d, t)); libre = t['j_out']
    return out
