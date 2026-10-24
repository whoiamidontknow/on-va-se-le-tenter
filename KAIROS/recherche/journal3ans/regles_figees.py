import numpy as np
# Règles figées AVANT l'ouverture de l'année de test (développement seulement)
def R_star(d):  return (d.dA60==1)&(d.dA240==1)&(d.eA<=0.6)
def R_alt(d):   return (d.dA60==1)&(d.dA240==1)&(d.eA<=1.5)
def R_simple(d): return (d.dA240==1)&(d.eA<=0.6)
