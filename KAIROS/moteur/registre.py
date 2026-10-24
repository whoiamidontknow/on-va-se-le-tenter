"""Registre des tests de KAIROS : une ligne par test dans registre/registre_tests.csv.

Plusieurs agents écrivent en même temps -> verrou exclusif (fcntl.flock) sur un fichier de verrou dédié pendant
la lecture du dernier id, l'écriture de la ligne et celle des trades.

    from registre import ajouter_test
    id_ = ajouter_test(dict(agent='tendance', famille='Signator', recette='sigF+trend60, stop 2 ATR',
                            marche='MNQ', ut_signal='15', ut_entree='15', echantillon='dev',
                            n_variantes_testees=24, verdict='rejeté', trades=trades))

- id automatique : PRÉFIXE-0001, préfixe = 3 premières lettres de l'agent en majuscules (ou `prefixe=`).
- `trades` (DataFrame du moteur) : écrit dans registre/trades/<id>.csv ; les colonnes n_trades, pct_gagnants,
  r_moyen, pf, gain_net_usd, dd_max_usd, periode_debut/fin manquantes sont calculées depuis ces trades.
- `fichier` vide -> chemin relatif du CSV des trades.
"""
import csv
import fcntl
import os
import re
import sys
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DOSSIER = os.path.abspath(os.path.join(HERE, '..', 'registre'))
CHAMPS = ['id', 'date', 'agent', 'famille', 'recette', 'marche', 'ut_signal', 'ut_entree', 'periode_debut',
          'periode_fin', 'echantillon', 'n_variantes_testees', 'n_trades', 'pct_gagnants', 'r_moyen', 'pf',
          'gain_net_usd', 'dd_max_usd', 'p_apex', 'p_tradeify', 'p_lucid', 'p_ref_hasard', 'verdict', 'fichier']


def _prefixe(agent):
    a = unicodedata.normalize('NFKD', str(agent)).encode('ascii', 'ignore').decode()
    a = re.sub(r'[^A-Za-z0-9]', '', a).upper()
    return (a[:3] or 'AGT')


def _fmt(v):
    if v is None:
        return ''
    if isinstance(v, float):
        if v != v:
            return ''
        return ('%.4f' % v).rstrip('0').rstrip('.')
    if isinstance(v, pd.Timestamp):
        return v.strftime('%Y-%m-%d %H:%M')
    return str(v)


def ajouter_test(ligne, dossier=None, prefixe=None):
    """Ajoute une ligne au registre (verrouillé) ; renvoie l'id attribué."""
    ligne = dict(ligne)
    dossier = dossier or DOSSIER
    os.makedirs(os.path.join(dossier, 'trades'), exist_ok=True)
    chemin = os.path.join(dossier, 'registre_tests.csv')
    trades = ligne.pop('trades', None)
    inconnues = set(ligne) - set(CHAMPS)
    if inconnues:
        raise KeyError('champs inconnus du registre : %s' % sorted(inconnues))
    if trades is not None and len(trades):
        sys.path.insert(0, HERE)
        from moteur import metriques
        m = metriques(trades, n_boot=1)
        auto = dict(n_trades=m['n'], pct_gagnants=m['pct_gagnants'], r_moyen=m['r_moyen'], pf=m['pf'],
                    gain_net_usd=m['gain_net_usd'], dd_max_usd=m['dd_max_usd'],
                    periode_debut=pd.Timestamp(trades['entree_t'].min()).strftime('%Y-%m-%d'),
                    periode_fin=pd.Timestamp(trades['sortie_t'].max()).strftime('%Y-%m-%d'))
        for k, v in auto.items():
            if ligne.get(k) in (None, ''):
                ligne[k] = v
    elif trades is not None and ligne.get('n_trades') in (None, ''):
        ligne['n_trades'] = 0
    pre = prefixe or _prefixe(ligne.get('agent', ''))
    with open(os.path.join(dossier, '.registre.lock'), 'a') as verrou:
        fcntl.flock(verrou, fcntl.LOCK_EX)
        try:
            n = 0
            neuf = not os.path.exists(chemin) or os.path.getsize(chemin) == 0
            if not neuf:
                with open(chemin, newline='') as fh:
                    for r in csv.DictReader(fh):
                        m_ = re.match(r'^%s-(\d+)$' % re.escape(pre), r.get('id') or '')
                        if m_:
                            n = max(n, int(m_.group(1)))
            id_ = '%s-%04d' % (pre, n + 1)
            ligne['id'] = id_
            if not ligne.get('date'):
                ligne['date'] = pd.Timestamp.now(tz='Europe/Paris').strftime('%Y-%m-%d %H:%M')
            if trades is not None:
                f = os.path.join(dossier, 'trades', id_ + '.csv')
                trades.to_csv(f, index=False)
                if not ligne.get('fichier'):
                    ligne['fichier'] = os.path.relpath(f, os.path.join(dossier, '..'))
            with open(chemin, 'a', newline='') as fh:
                w = csv.writer(fh)
                if neuf:
                    w.writerow(CHAMPS)
                w.writerow([_fmt(ligne.get(k)) for k in CHAMPS])
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            fcntl.flock(verrou, fcntl.LOCK_UN)
    return id_
