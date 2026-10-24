"""Catalogue de setups = déclencheur × sens × filtre × sortie (toutes les confluences lisibles dans le dataset).

Tous les tableaux sont lus à la CLÔTURE de la barre signal ; le moteur entre à l'ouverture suivante.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def _croise_haut(x: pd.Series, niv: pd.Series) -> np.ndarray:
    a = (x > niv) & ~(x.shift(1) > niv.shift(1)) & niv.notna() & niv.shift(1).notna()
    return a.to_numpy()


def _premier_par(ev: np.ndarray, groupe: np.ndarray) -> np.ndarray:
    """Garde le 1er événement de chaque groupe (jour, semaine...)."""
    s = pd.Series(ev.astype(int)).groupby(groupe).cumsum().to_numpy()
    return ev & (s == 1)


def declencheurs(d: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """nom -> (long, short) booléens. d = DataFrame avec les briques d'etats.briques."""
    b = lambda c: d[c].fillna(False).astype(bool).to_numpy() if c in d else np.zeros(len(d), bool)
    out = {
        'sigF': (b('sig_long_fort'), b('sig_short_fort')),
        'sigFM': (b('sig_long_fort') | b('sig_long_moyen'), b('sig_short_fort') | b('sig_short_moyen')),
        'heiflip': (b('hei_flip_haut'), b('hei_flip_bas')),
        'clx': (b('clx_buy'), b('clx_sell')),
        'tl': (b('tl_cassure_haut'), b('tl_cassure_bas')),
        # zone baissière cassée par le haut (mitigée) -> long ; zone haussière cassée par le bas -> short
        'det': (b('zb_mitigee'), b('zh_mitigee')),
    }
    jour = d.index.tz_convert('America/New_York').normalize().asi8
    out['orb'] = (_premier_par(_croise_haut(d['c'], d['orb_h_r']), jour),
                  _premier_par(_croise_haut(-d['c'], -d['orb_l_r']), jour))
    p = d.index.tz_convert('Europe/Paris').isocalendar()
    sem = (p.year * 100 + p.week).to_numpy()
    out['mon'] = (_premier_par(_croise_haut(d['c'], d['mon_h_r']), sem),
                  _premier_par(_croise_haut(-d['c'], -d['mon_l_r']), sem))
    f = d['feu'].to_numpy(); f1 = np.r_[0, f[:-1]]
    out['feu'] = ((f == 1) & (f1 != 1), (f == -1) & (f1 != -1))
    # pas de signal sur les 100 premières barres (indicateurs en chauffe)
    for k, (L, S) in out.items():
        L = L.copy(); S = S.copy(); L[:100] = False; S[:100] = False
        out[k] = (L, S)
    return out


def filtres(d: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """nom -> (autorise_long, autorise_short)."""
    un = np.ones(len(d), bool)
    t60 = d['trend_60'].astype(bool).to_numpy() & d.get('ok_trend_60', pd.Series(True, index=d.index)).to_numpy()
    t60s = ~d['trend_60'].astype(bool).to_numpy() & d.get('ok_trend_60', pd.Series(True, index=d.index)).to_numpy()
    return {
        'aucun': (un, un),
        'trend60': (t60, t60s),
        'hei60': (d['hei60'].to_numpy() == 1, d['hei60'].to_numpy() == -1),
        'feu': (d['feu'].to_numpy() == 1, d['feu'].to_numpy() == -1),
        'ema50': (d['au_ema'].to_numpy() == 1, d['au_ema'].to_numpy() == -1),
        'adx20': (d['adx'].to_numpy() >= 20, d['adx'].to_numpy() >= 20),
    }


SENS = ['long', 'short', 'les_deux']

SORTIES = {
    'A2_2R': dict(stop={'mode': 'atr', 'k': 2.0}, objectif={'mode': 'R', 'k': 2.0}),
    'A1_1.5R': dict(stop={'mode': 'atr', 'k': 1.0}, objectif={'mode': 'R', 'k': 1.5}),
    'A2_hei': dict(stop={'mode': 'atr', 'k': 2.0}, objectif={'mode': 'aucun'}, sortie_signal='hei'),
    'A2_3R_be1': dict(stop={'mode': 'atr', 'k': 2.0}, objectif={'mode': 'R', 'k': 3.0},
                      break_even={'R': 1.0, 'ticks': 1}),
}

DECLENCHEURS = ['sigF', 'sigFM', 'heiflip', 'clx', 'tl', 'det', 'orb', 'mon', 'feu']
FILTRES = ['aucun', 'trend60', 'hei60', 'feu', 'ema50', 'adx20']


def catalogue() -> list[tuple[str, str, str, str]]:
    return list(itertools.product(DECLENCHEURS, SENS, FILTRES, SORTIES))


def nom_setup(s) -> str:
    return '%s|%s|%s|%s' % s


def gestion(sortie: str, instrument: str, d: pd.DataFrame) -> dict:
    g = dict(SORTIES[sortie])
    if g.get('sortie_signal') == 'hei':
        bleu = d['hei_bleu'].astype(bool).to_numpy()
        g['sortie_signal'] = {'long': ~bleu, 'short': bleu}
    g['instrument'] = instrument
    return g


def signaux(s, D: dict, F: dict) -> tuple[np.ndarray, np.ndarray]:
    dec, sens, fil, _ = s
    L, S = D[dec]
    fl, fs = F[fil]
    L = L & fl if sens in ('long', 'les_deux') else np.zeros_like(L)
    S = S & fs if sens in ('short', 'les_deux') else np.zeros_like(S)
    return L, S
