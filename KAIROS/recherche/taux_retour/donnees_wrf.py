"""Agent « Taux — retour à la moyenne » (WRF). TOUT l'accès aux données passe par `charger_series()`.

Passage au DATASET : variable d'environnement WRF_SOURCE=dataset (ou charger_series('dataset')), puis tout relancer.
On réutilise le chargeur du méta-modèle (recherche/meta_ml/donnees.py) : mêmes séries 15 min, même format de
colonnes que dataset/charger.py, coupées au DÉVELOPPEMENT (75 %) par moteur.charger_recherche. Le scellé n'est
jamais lu ici.

Prix utilisés pour les SIGNAUX : colonnes *_causal si elles existent (source cache : reconstitution en passe
avant seule, aucune information de la barre suivante), sinon les vrais prix o/h/l/c (DATASET).
Le MOTEUR exécute toujours sur o/h/l/c.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
for p in (os.path.join(SB, 'moteur'), os.path.join(SB, 'propfirm'), os.path.join(SB, 'recherche', 'meta_ml')):
    if p not in sys.path:
        sys.path.insert(0, p)

SOURCE = os.environ.get('WRF_SOURCE', 'cache')


def charger_series(source=None):
    """-> liste de dicts {nom, instrument ('MES'|'MNQ'), ut_min, df} ; df = développement seulement."""
    import donnees as _d          # recherche/meta_ml/donnees.py
    return _d.charger_series(source or SOURCE, ut='15')


def col(df, nom, defaut=np.nan):
    return df[nom].to_numpy(dtype=float) if nom in df.columns else np.full(len(df), defaut)


def bool_col(df, nom):
    return df[nom].fillna(False).to_numpy(dtype=bool) if nom in df.columns else np.zeros(len(df), bool)


def prix_signal(df):
    """(o, h, l, c, atr) connus à la clôture, sans regard vers le futur."""
    g = lambda k: col(df, k + '_causal') if k + '_causal' in df.columns else col(df, k)
    a = col(df, 'atr_causal') if 'atr_causal' in df.columns else col(df, 'atr')
    return g('o'), g('h'), g('l'), g('c'), a


def jour_cme(idx):
    ch = idx.tz_convert('America/Chicago')
    return (ch + pd.Timedelta(hours=7)).normalize().tz_localize(None).to_numpy()
