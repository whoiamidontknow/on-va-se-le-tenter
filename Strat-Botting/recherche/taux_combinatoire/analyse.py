"""Étape 3 : biais de sélection (bootstrap de White), walk-forward de la procédure, hypothèse « nuit » fixée à
l'avance, choix des recettes. Écrit sorties/analyse_<source>.pkl, sorties/balayage_complet.csv.gz,
sorties/wf_procedure.csv, sorties/candidats.csv.

    ~/venv-quant/bin/python analyse.py [--source cache|dataset]
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import balayage as BA  # noqa: E402
import bib_wrx as B  # noqa: E402
import donnees_wrx as D  # noqa: E402
import tables as TB  # noqa: E402

SORTIES = TB.SORTIES
TAUX_MIN, TAUX_MAX = 0.60, 0.75
N_MIN_DEV = 60
N_MIN_TRAIN = 25
N_BOOT = 1000
BLOC_MOYEN = 5
K_PLIS, RATIO = 4, 3


# ════════════════════════════════════════════════════════════════════════════════════════
# White (Reality Check studentisé, bootstrap stationnaire par journées), p ajustées pas unique
# ════════════════════════════════════════════════════════════════════════════════════════
def indices_stationnaires(nd, nb, bloc, rng):
    out = np.empty((nb, nd), np.int64)
    p = 1.0 / bloc
    for b in range(nb):
        i = rng.integers(nd)
        for t in range(nd):
            if t > 0:
                i = rng.integers(nd) if rng.random() < p else (i + 1) % nd
            out[b, t] = i
    return out


def white(X, n_boot=N_BOOT, bloc=BLOC_MOYEN, graine=0):
    """X : (V, ND) écarts journaliers. Renvoie (t observés, p ajustée pour chaque variante = P(max t* >= t_k),
    p du Reality Check pour la meilleure)."""
    V, ND = X.shape
    mu = X.mean(1, dtype=np.float64)
    sd = X.std(1, ddof=1, dtype=np.float64)
    sd = np.where(sd > 0, sd, np.inf)
    t = np.sqrt(ND) * mu / sd
    rng = np.random.default_rng(graine)
    I = indices_stationnaires(ND, n_boot, bloc, rng)
    C = np.stack([np.bincount(I[b], minlength=ND) for b in range(n_boot)], 1).astype(np.float32)   # (ND, B)
    mx = np.empty(n_boot)
    pas = 20000
    for b0 in range(0, n_boot, 100):
        Cb = C[:, b0:b0 + 100]
        m = np.full(Cb.shape[1], -np.inf)
        for v0 in range(0, V, pas):
            mb = (X[v0:v0 + pas] @ Cb) / ND                                      # moyennes bootstrap
            ts = np.sqrt(ND) * (mb - mu[v0:v0 + pas, None]) / sd[v0:v0 + pas, None]
            m = np.maximum(m, ts.max(0))
        mx[b0:b0 + Cb.shape[1]] = m
    mx_s = np.sort(mx)
    p_adj = 1.0 - np.searchsorted(mx_s, t, side='left') / n_boot
    p_adj = (1 + p_adj * n_boot) / (1 + n_boot)
    return t, p_adj, float(p_adj[np.argmax(t)]), mx


# ════════════════════════════════════════════════════════════════════════════════════════
def stats_blocs(BL, blocs):
    s = BL[:, :, blocs].sum(2).astype(np.float64)
    n, w, p0, v0, r, r0, gp, gm = (s[:, k] for k in range(8))
    with np.errstate(invalid='ignore', divide='ignore'):
        return pd.DataFrame(dict(n=n, taux=w / n, taux_placebo=p0 / n, ecart_pts=100 * (w - p0) / n,
                                 z_ecart=(w - p0) / np.sqrt(v0), r_moyen=r / n, ecart_r=(r - r0) / n,
                                 pf=np.where(gm > 0, gp / np.where(gm > 0, gm, 1), np.inf), w=w, p0=p0, r=r, r0=r0,
                                 gp=gp, gm=gm))


def eligible(S, n_min):
    return ((S['n'] >= n_min) & (S['taux'] >= TAUX_MIN) & (S['taux'] <= TAUX_MAX) & (S['r_moyen'] > 0)
            & (S['pf'] > 1)).to_numpy()


def procedure_wf(lig, BL):
    """Pli p : choisir sur les blocs [p, p+3) la variante éligible de plus fort z d'écart de taux, la jouer sur le
    bloc p+3. Renvoie le détail par pli et l'agrégat hors échantillon (top 1 et top 10)."""
    plis = []
    for p in range(K_PLIS):
        Str = stats_blocs(BL, list(range(p, p + RATIO)))
        Ste = stats_blocs(BL, [p + RATIO])
        el = eligible(Str, N_MIN_TRAIN)
        cand = np.flatnonzero(el)
        ordre = cand[np.argsort(-Str['z_ecart'].to_numpy()[cand])]
        top = ordre[:10]
        k1 = int(ordre[0]) if len(ordre) else -1
        plis.append(dict(pli=p, n_eligibles=len(cand), choix=k1, top10=top.tolist(),
                         train=Str.iloc[k1].to_dict() if k1 >= 0 else {}, test=Ste.iloc[k1].to_dict() if k1 >= 0 else {},
                         test_top10=Ste.iloc[top][['n', 'w', 'p0', 'r', 'r0', 'gp', 'gm']].sum().to_dict(),
                         test_tous_elig=Ste.iloc[cand][['n', 'w', 'p0', 'r', 'r0']].sum().to_dict()))
    return plis


def agreger(dlist):
    s = pd.DataFrame(dlist)[['n', 'w', 'p0', 'r', 'r0', 'gp', 'gm']].sum()
    return dict(n=s.n, taux=s.w / s.n, taux_placebo=s.p0 / s.n, ecart_pts=100 * (s.w - s.p0) / s.n,
                r_moyen=s.r / s.n, ecart_r=(s.r - s.r0) / s.n, pf=s.gp / s.gm if s.gm > 0 else np.inf)


def nom_variante(l):
    return '%s|%s|%dm|%s|%s' % (l['decl'], l['sens'], l['ut'], l['filtres'], B.nom_geo((l['stop'], l['obj'], l['extra'])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=D.SOURCE)
    a = ap.parse_args()
    t0 = time.time()
    lig, BL, WI, EW, ER, n_teste = BA.charger_balayage(a.source)
    lig['variante'] = [nom_variante(l) for l in lig.to_dict('records')]
    print('variantes testées %d ; évaluées (>= %d signaux) %d ; dans White (>= %d trades) %d' % (
        n_teste, BA.NSIG_MIN, len(lig), BA.N_WHITE, len(WI)), flush=True)
    # ---- White sur l'écart de taux et sur l'écart de R
    tW, pW, pW_best, _ = white(EW)
    tR, pR, pR_best, _ = white(ER, graine=1)
    lig['t_white_taux'] = np.nan; lig['p_white_taux'] = np.nan; lig['t_white_r'] = np.nan; lig['p_white_r'] = np.nan
    lig.loc[WI, 't_white_taux'] = tW; lig.loc[WI, 'p_white_taux'] = pW
    lig.loc[WI, 't_white_r'] = tR; lig.loc[WI, 'p_white_r'] = pR
    print('White écart de taux : meilleure t=%.2f p=%.3f (%s)' % (tW.max(), pW_best, lig.loc[WI[np.argmax(tW)], 'variante']))
    print('White écart de R    : meilleure t=%.2f p=%.3f (%s)' % (tR.max(), pR_best, lig.loc[WI[np.argmax(tR)], 'variante']))
    # ---- critères sur le développement entier
    el = eligible(lig, N_MIN_DEV)
    lig['eligible_dev'] = el
    # stabilité : blocs (sur 7) où l'écart de taux est positif
    pos = 0
    for q in range(BA.NBLOCS):
        Sq = stats_blocs(BL, [q])
        pos = pos + ((Sq['n'] > 0) & (Sq['w'] > Sq['p0'])).to_numpy().astype(int)
    lig['blocs_ecart_pos'] = pos
    lig['blocs_actifs'] = (BL[:, 0, :] > 0).sum(1)
    # ---- walk-forward de la procédure
    plis = procedure_wf(lig, BL)
    rows = []
    for p in plis:
        k = p['choix']
        rows.append(dict(pli=p['pli'], n_eligibles=p['n_eligibles'], choix=lig.loc[k, 'variante'] if k >= 0 else '',
                         taux_train=p['train'].get('taux'), z_train=p['train'].get('z_ecart'), n_train=p['train'].get('n'),
                         n_test=p['test'].get('n'), taux_test=p['test'].get('taux'),
                         placebo_test=p['test'].get('taux_placebo'), r_test=p['test'].get('r_moyen'),
                         pf_test=p['test'].get('pf')))
    wf = pd.DataFrame(rows)
    wf.to_csv(os.path.join(SORTIES, 'wf_procedure.csv'), index=False, float_format='%.4f')
    print(wf.to_string())
    oos1 = agreger([p['test'] for p in plis if p['choix'] >= 0])
    oos10 = agreger([p['test_top10'] for p in plis])
    print('hors échantillon top 1 :', {k: round(float(v), 3) for k, v in oos1.items()})
    print('hors échantillon top 10 :', {k: round(float(v), 3) for k, v in oos10.items()})
    # ---- candidats (développement entier) : éligibles, triés par z d'écart de taux, un par famille
    C = lig[el].sort_values('z_ecart', ascending=False)
    C.head(200).to_csv(os.path.join(SORTIES, 'candidats.csv'), index=False, float_format='%.4f')
    cols = ['variante', 'n', 'taux', 'taux_placebo', 'ecart_pts', 'z_ecart', 'r_moyen', 'ecart_r', 'pf', 'blocs_ecart_pos',
            'p_white_taux', 'p_white_r']
    print(C[cols].head(25).to_string())
    lig.drop(columns=[]).to_csv(os.path.join(SORTIES, 'balayage_complet.csv.gz'), index=False, float_format='%.4f')
    with open(os.path.join(SORTIES, 'analyse_%s.pkl' % a.source), 'wb') as fh:
        pickle.dump(dict(n_teste=n_teste, n_eval=len(lig), n_white=len(WI), pW_best=pW_best, pR_best=pR_best,
                         tW_best=float(tW.max()), tR_best=float(tR.max()),
                         best_W=lig.loc[WI[np.argmax(tW)], 'variante'], best_R=lig.loc[WI[np.argmax(tR)], 'variante'],
                         plis=plis, oos1=oos1, oos10=oos10, n_eligibles_dev=int(el.sum())), fh)
    print('analyse : %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
