"""Étape 2 : balayage déclencheur × sens × UT × (0 à 3 filtres) × géométrie, avec placebo exact de même géométrie.

    ~/venv-quant/bin/python balayage.py [--source cache|dataset]
Lit sorties/tables_<source>.pkl (tables.py). Écrit un morceau par (UT, déclencheur, sens) dans
sorties/morceaux_<source>/ (reprise possible : un morceau déjà écrit n'est pas recalculé).

Par variante (développement entier) : n, gagnants, taux placebo (moyenne exacte des tirages « même heure, même
sens, même géométrie »), écart de taux et son z, R moyen, R placebo, PF ($), + sommes par bloc de walk-forward
(7 blocs de journées par jeu, comme moteur.walk_forward(k=4, ratio=3)) et séries journalières des écarts (taux et
R) pour le bootstrap de White (variantes à >= N_WHITE trades).
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import bib_wrx as B  # noqa: E402
import donnees_wrx as D  # noqa: E402
import tables as TB  # noqa: E402

M = D.M
NSIG_MIN = 20          # en dessous (signaux du développement), la variante est comptée mais pas évaluée
N_WHITE = 30           # trades minimum pour entrer dans le bootstrap de White
NBLOCS = 7             # walk_forward(k=4, ratio=3) : 7 blocs de journées par jeu
# quantités par bloc : n, gagnants, p0, p0(1-p0), r, r0, pnl+, pnl-
QB = 8

_ETAT = {}


def preparer(source):
    jeux = D.charger_jeux(source)
    T = TB.construire(source)
    tous_jours = np.unique(np.concatenate([T[(ji, B.geometries()[0])]['jour'] for ji in range(len(jeux))]))
    prep = []
    for ji, j in enumerate(jeux):
        df = j['df']
        tab0 = T[(ji, B.geometries()[0])]
        jour = tab0['jour']
        uj = np.unique(jour)
        bornes = np.linspace(0, len(uj), NBLOCS + 1).round().astype(int)
        bloc_j = np.zeros(len(uj), np.int64)
        for q in range(NBLOCS):
            bloc_j[bornes[q]:bornes[q + 1]] = q
        bloc = bloc_j[np.searchsorted(uj, jour)]
        dec = {k: B.declencheur(df, k) for k in B.DECLENCHEURS}
        P = {}
        for g in B.geometries():
            pw, pr, _ = B.placebo_moyen(T[(ji, g)])
            h = T[(ji, g)]['heure']
            P[g] = (pw[:, h], pr[:, h])          # (2, n) : placebo moyen pour un signal à cette barre
        prep.append(dict(nom=j['nom'], ut=j['ut'], marche=j['marche'], dec=dec, filtres=B.masques_filtres(df),
                         jgl=np.searchsorted(tous_jours, jour), bloc=bloc, P=P))
    return jeux, T, prep, tous_jours


def _init(source):
    _ETAT['jeux'], _ETAT['T'], _ETAT['prep'], _ETAT['jours'] = preparer(source)


def signaux(p, dec, sens, fset):
    """(L, S) d'une variante sur un jeu ; None si un filtre n'existe pas sur ce jeu. Règle Pine : un long exige
    sig_long ET PAS sig_short (déclencheurs bruts), filtres appliqués ensuite."""
    L0, S0 = p['dec'][dec]
    L = L0 & ~S0; S = S0 & ~L0
    for f in fset:
        if f not in p['filtres']:
            return None
        a, b = p['filtres'][f]
        L = L & a; S = S & b
    if sens == 'long':
        S = np.zeros_like(S)
    elif sens == 'short':
        L = np.zeros_like(L)
    return L, S


def trades_variante(T, prep, jis, dec, sens, fset, g):
    """Concatène les trades d'une variante sur ses jeux : dict de tableaux (une ligne par trade)."""
    parts = []
    for ji in jis:
        p = prep[ji]
        s = signaux(p, dec, sens, fset)
        if s is None:
            return None
        tab = T[(ji, g)]
        idx, d = TB.trades_table(tab, *s)
        parts.append((ji, idx, d))
    return parts


def _morceau(args):
    ut, dec, sens, chemin = args
    T, prep, jours = _ETAT['T'], _ETAT['prep'], _ETAT['jours']
    jis = [ji for ji, p in enumerate(prep) if p['ut'] == ut]
    ND = len(jours)
    geos = B.geometries()
    lignes, blocs, white_i, EW, ER = [], [], [], [], []
    n_teste = 0
    for fset in B.combinaisons():
        sig = []
        for ji in jis:
            s = signaux(prep[ji], dec, sens, fset)
            if s is None:
                break
            sig.append((ji, s))
        if len(sig) < len(jis):
            continue                                  # filtre inexistant à cette UT (ex. TREND 60 en 60 min)
        n_teste += len(geos)
        nsig = sum(int(s[0].sum() + s[1].sum()) for _, s in sig)
        if nsig < NSIG_MIN:
            continue
        for g in geos:
            cols = {k: [] for k in ('w', 'r', 'pnl', 'p0', 'r0', 'jgl', 'bloc', 'mes')}
            for ji, s in sig:
                tab = T[(ji, g)]
                idx, d = TB.trades_table(tab, *s)
                if not len(idx):
                    continue
                p = prep[ji]
                cols['w'].append(tab['gagne'][d, idx]); cols['r'].append(tab['r'][d, idx])
                cols['pnl'].append(tab['pnl'][d, idx])
                cols['p0'].append(p['P'][g][0][d, idx]); cols['r0'].append(p['P'][g][1][d, idx])
                cols['jgl'].append(p['jgl'][idx]); cols['bloc'].append(p['bloc'][idx])
                cols['mes'].append(np.full(len(idx), p['marche'] == 'MES'))
            if not cols['w']:
                continue
            c = {k: np.concatenate(v) for k, v in cols.items()}
            n = len(c['w'])
            w = c['w'].astype(float); r = c['r']; pnl = c['pnl']; p0 = c['p0']; r0 = c['r0']
            gp, gm = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
            v0 = (p0 * (1 - p0)).sum()
            sr = r.std(ddof=1) if n > 1 else np.nan
            mes = c['mes']
            lignes.append(dict(
                ut=ut, decl=dec, sens=sens, filtres='+'.join(fset) if fset else '-', nf=len(fset),
                stop=g[0], obj=g[1], extra=g[2], n=n, taux=w.mean(), taux_placebo=p0.mean(),
                ecart_pts=100 * (w.mean() - p0.mean()), z_ecart=(w.sum() - p0.sum()) / np.sqrt(v0) if v0 > 0 else np.nan,
                r_moyen=r.mean(), r_placebo=r0.mean(), ecart_r=r.mean() - r0.mean(),
                t_r=r.mean() / (sr / np.sqrt(n)) if sr and sr > 0 else np.nan,
                pf=gp / gm if gm > 0 else np.inf, net_usd=pnl.sum(),
                n_mes=int(mes.sum()), r_mes=r[mes].mean() if mes.any() else np.nan,
                r_nq=r[~mes].mean() if (~mes).any() else np.nan,
                taux_mes=w[mes].mean() if mes.any() else np.nan, taux_nq=w[~mes].mean() if (~mes).any() else np.nan))
            b = c['bloc']
            blocs.append(np.stack([np.bincount(b, weights=x, minlength=NBLOCS) for x in
                                   (np.ones(n), w, p0, p0 * (1 - p0), r, r0, np.maximum(pnl, 0), np.maximum(-pnl, 0))],
                                  0).astype(np.float32))
            if n >= N_WHITE:
                white_i.append(len(lignes) - 1)
                EW.append(np.bincount(c['jgl'], weights=w - p0, minlength=ND).astype(np.float32))
                ER.append(np.bincount(c['jgl'], weights=r - r0, minlength=ND).astype(np.float32))
    out = dict(lignes=pd.DataFrame(lignes), blocs=np.array(blocs, np.float32).reshape(-1, QB, NBLOCS),
               white_i=np.array(white_i, np.int64),
               EW=np.array(EW, np.float32).reshape(-1, ND), ER=np.array(ER, np.float32).reshape(-1, ND),
               n_teste=n_teste)
    with open(chemin, 'wb') as fh:
        pickle.dump(out, fh)
    return ut, dec, sens, len(lignes), n_teste


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=D.SOURCE)
    a = ap.parse_args()
    dos = os.path.join(TB.SORTIES, 'morceaux_%s' % a.source)
    os.makedirs(dos, exist_ok=True)
    taches = []
    for ut in D.UTS:
        for dec in B.DECLENCHEURS:
            for sens in B.SENS:
                ch = os.path.join(dos, '%d_%s_%s.pkl' % (ut, dec, sens))
                if not os.path.exists(ch):
                    taches.append((ut, dec, sens, ch))
    t0 = time.time()
    print('%d morceaux à calculer' % len(taches), flush=True)
    if taches:
        with ProcessPoolExecutor(8, initializer=_init, initargs=(a.source,)) as ex:
            for r in ex.map(_morceau, taches):
                print('  %s : %d variantes évaluées / %d testées  (%.0f s)' % (r[:3], r[3], r[4], time.time() - t0),
                      flush=True)
    print('balayage fini en %.0f s' % (time.time() - t0))


def charger_balayage(source):
    """Assemble les morceaux : (lignes DataFrame, blocs (V, QB, 7), white_idx, EW, ER, n_variantes_testees)."""
    dos = os.path.join(TB.SORTIES, 'morceaux_%s' % source)
    L, BL, WI, EW, ER = [], [], [], [], []
    n_teste = 0; dec = 0
    for f in sorted(os.listdir(dos)):
        with open(os.path.join(dos, f), 'rb') as fh:
            o = pickle.load(fh)
        L.append(o['lignes']); BL.append(o['blocs']); WI.append(o['white_i'] + dec)
        EW.append(o['EW']); ER.append(o['ER'])
        dec += len(o['lignes']); n_teste += o['n_teste']
    lig = pd.concat(L, ignore_index=True)
    return lig, np.concatenate(BL), np.concatenate(WI), np.concatenate(EW), np.concatenate(ER), n_teste


if __name__ == '__main__':
    main()
