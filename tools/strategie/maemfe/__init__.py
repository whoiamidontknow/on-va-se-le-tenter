"""Étude du stop et de la sortie par MAE/MFE (indépendante de l'entrée). Voir run.py et etude.py."""
import os, sys
_H = os.path.dirname(os.path.abspath(__file__))
if _H not in sys.path:
    sys.path.insert(0, _H)
from etude import univers, entrees_univers, profil, recommander, evaluer_plan, etudier  # noqa: E402,F401
from core import Univers, simuler, excursions  # noqa: E402,F401
from donnees import charger_series, selectionner, DECLENCHEURS  # noqa: E402,F401
