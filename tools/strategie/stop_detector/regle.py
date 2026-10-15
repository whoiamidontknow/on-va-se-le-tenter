"""Règle de stop « Zone Detector la plus proche » de STRATEGIE_V1.pine (f_stop), reproduite à l'identique.

Pine (signal connu à la clôture de la barre i, entrée à l'ouverture de i+1) :
  e = vrai close de i (r_c) ; r_atr = RMA(TR, 14) sur vrais prix ;
  long  : best = plus HAUT des bas (btm) des zones HAUSSIÈRES actives tel que btm < e ; cand = best - marge ;
  short : best = plus BAS des hauts (top) des zones BAISSIÈRES actives tel que top > e ; cand = best + marge ;
  zone utilisable si x_detMin*ATR <= |e - cand| <= x_detMax*ATR, sinon repli sur ATR x k.
  Toutes les zones actives des tableaux comptent (pas seulement les 3 du filtre « det_nZones »).
  La DISTANCE est ensuite conservée depuis le vrai prix de remplissage (lossTk relatif, puis recalage).
Zones : features.detector (OB LuxAlgo, mitigation mèche, longueur 5, sur bougies HA), 19/19 zones identiques
à l'API ; ici sans troncature à 3 zones, et avec le volume brut (inconnu -> -1, comme features.build_series).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
STRAT = os.path.abspath(os.path.join(HERE, '..'))
for p in (STRAT, os.path.join(STRAT, 'maemfe')):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np
import data, features, build_all   # noqa: E402
import donnees as md               # maemfe/donnees.py : instrument, SPEC, selectionner  # noqa: E402

MARGE_TK = 2
DMIN, DMAX = 0.3, 4.0


def zones_completes(S, seg):
    """Toutes les zones actives à la clôture de chaque barre : (Zb, Zs) listes de (top, btm)."""
    vraw = [r['v'] for r in seg]
    Zb, Zs, _, _ = features.detector(S['o'], S['h'], S['l'], S['c'],
                                     [x if x is not None else -1.0 for x in vraw], length=5, keep=10 ** 9)
    return Zb, Zs


def charger(tfs=(5, 15, 30, 60)):
    """Séries du cache commun (sans chevauchement, avec volume), enrichies des zones complètes."""
    S_all = md.selectionner(build_all.load(), tfs)
    D = data.load()
    out = []
    for S in S_all:
        if not S['hasv']: continue
        segs = D.get((S['sym'], S['tf']), [])
        seg = next((g for g in segs if len(g) == S['n'] and g[0]['t'] == S['T'][0]), None)
        if seg is None:
            print('segment brut introuvable', S['sym'], S['tf']); continue
        S['ZbF'], S['ZsF'] = zones_completes(S, seg)
        # contrôle : les 3 premières zones = celles de features (cache)
        assert all(S['ZbF'][i][:3] == list(S['Zb'][i]) and S['ZsF'][i][:3] == list(S['Zs'][i]) for i in range(S['n']))
        S['inst'] = md.instrument(S['sym'])
        out.append(S)
    return out


def niveau_detector(S, i, d, tick=0.25, marge=MARGE_TK):
    """Niveau candidat (cand) de la zone la plus proche, ou None. Prix de référence e = vrai close de i."""
    e = S['rc'][i]
    best = None
    if d > 0:
        for top, btm in S['ZbF'][i]:
            if btm < e and (best is None or btm > best): best = btm
    else:
        for top, btm in S['ZsF'][i]:
            if top > e and (best is None or top < best): best = top
    if best is None: return None
    return best - marge * tick if d > 0 else best + marge * tick


def distance_stop(S, i, d, mode, k=1.5, tick=0.25, dmin=DMIN, dmax=DMAX):
    """Distance du stop en POINTS (f_stop du Pine) et indicateur « zone utilisée ».
    mode : 'atr' (ATR x k) ou 'det' (zone Detector, repli ATR x k)."""
    a = S['ratr'][i]
    if mode == 'det':
        cand = niveau_detector(S, i, d, tick)
        if cand is not None:
            d0 = abs(S['rc'][i] - cand)
            if dmin * a <= d0 <= dmax * a:
                return d0, True
    return k * a, False
