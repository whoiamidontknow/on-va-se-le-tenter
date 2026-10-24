"""Accès aux données de l'agent « Taux — combinatoire de confluences » (WRX).

TOUT l'accès aux données passe par `charger_jeux()`. Pour passer au DATASET : `charger_jeux('dataset')`
(ou WRX_SOURCE=dataset) ; le reste du code ne change pas.

On réutilise le chargeur de l'explorateur exhaustif (`recherche/exhaustif/donnees_exh.py` : cache Python ou
DATASET, enrichissement sans regard vers le futur, partie DÉVELOPPEMENT seulement, scellé non ouvert), puis on
ajoute les colonnes propres à STRATEGIE_V1.pine :
- `lvl_up / lvl_dn` : cassure (clôture) d'un niveau de session terminée (Asie, Londres, US) ou du Monday
  High / Low, chaque niveau ne servant qu'une fois, niveaux gardés 2 jours (règle de f_ses dans le Pine) ;
- `clx_dernier` : sens du dernier climax (+1 / -1 / 0), pour le filtre « ne jamais trader contre » ;
- `feu_pL / feu_pS` : part (%) des voix du Feu dans chaque sens (substitut de Feu si le vrai manque).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'exhaustif'))
import donnees_exh as DX  # noqa: E402

M = DX.M
SB = DX.SB
SOURCE = os.environ.get('WRX_SOURCE', 'cache')
UTS = (15, 30, 60)          # 5 min : 4-5 jours seulement dans le cache -> exclu


def charger_jeux(source=None, uts=UTS):
    """Point d'entrée UNIQUE : liste de jeux dict(nom, marche, instrument, ut, df), développement seulement."""
    source = source or SOURCE
    jeux = DX.charger_jeux(source=source, uts=uts)
    out = []
    for j in jeux:
        j = dict(j)
        j['df'] = completer(j['df'])
        out.append(j)
    return out


# ════════════════════════════════════════════════════════════════════════════════════════
def _cassures_sessions(df):
    """Niveaux haut / bas des sessions terminées, surveillés 2 jours, retirés à leur 1re cassure (clôture)."""
    n = len(df)
    c = df['c'].to_numpy(float); h = df['h'].to_numpy(float); l = df['l'].to_numpy(float)
    up = np.zeros(n, bool); dn = np.zeros(n, bool)
    for tz, a0, b0 in (('Asia/Tokyo', 540, 930), ('Europe/London', 480, 990), ('America/New_York', 570, 960)):
        loc = df.index.tz_convert(tz)
        mins = (loc.hour * 60 + loc.minute).to_numpy()
        jour = (loc.normalize().tz_localize(None).asi8 // (86400 * 10 ** 9)).astype(np.int64)
        ins = (mins >= a0) & (mins < b0)
        run = False; H = L = np.nan; jr = 0
        niveaux = []                       # [prix, haut?, jour]
        for i in range(n):
            if i > 0 and not ins[i] and ins[i - 1] and run:
                niveaux.append([H, True, jr]); niveaux.append([L, False, jr]); run = False
            if ins[i] and (i == 0 or not ins[i - 1]):
                jr = jour[i]; H = h[i]; L = l[i]; run = True
            elif ins[i] and run:
                H = max(H, h[i]); L = min(L, l[i])
            if niveaux:
                garde = []
                for p, hi, jj in niveaux:
                    vieux = jj <= jour[i] - 2
                    trav = (c[i] > p) if hi else (c[i] < p)
                    if vieux or trav:
                        if trav and not vieux:
                            if hi:
                                up[i] = True
                            else:
                                dn[i] = True
                        continue
                    garde.append([p, hi, jj])
                niveaux = garde
    # Monday High / Low (vrais prix, Paris) : une cassure de chaque côté par semaine, après la fin du lundi
    pa = df.index.tz_convert('Europe/Paris')
    wd = pa.weekday.to_numpy(); mpa = (pa.hour * 60 + pa.minute).to_numpy()
    iso = pa.isocalendar(); sem = (iso['year'].to_numpy() * 100 + iso['week'].to_numpy())
    lundi = (wd == 0) | ((wd == 1) & (mpa < 450))
    sm = -1; mh = ml = np.nan; pret = False; fh = fb = True
    for i in range(n):
        if sem[i] != sm:
            sm = sem[i]; mh = ml = np.nan; pret = False; fh = fb = True
        if lundi[i]:
            mh = h[i] if mh != mh else max(mh, h[i]); ml = l[i] if ml != ml else min(ml, l[i])
            continue
        if not pret and mh == mh:
            pret = True; fh = fb = False
        if pret:
            if not fh and c[i] > mh:
                up[i] = True; fh = True
            if not fb and c[i] < ml:
                dn[i] = True; fb = True
    return up, dn


def completer(df):
    df = df.copy()
    up, dn = _cassures_sessions(df)
    df['lvl_up'] = up; df['lvl_dn'] = dn
    cx = np.where(df['clx_buy'].to_numpy(bool), 1.0, np.where(df['clx_sell'].to_numpy(bool), -1.0, np.nan))
    df['clx_dernier'] = pd.Series(cx).ffill().fillna(0.0).to_numpy()
    f = df['feu_net'].to_numpy(float)
    df['feu_pL'] = 50.0 * (1.0 + f); df['feu_pS'] = 50.0 * (1.0 - f)
    return df
