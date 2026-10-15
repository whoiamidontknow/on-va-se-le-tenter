"""Espace de recherche : lecture de config.toml, tirage, forme canonique, voisins (plateau), masques de
filtres sur l'univers, et traduction d'un réglage en bloc de réglages STRATEGIE_V1.pine."""
import tomllib
import numpy as np

SIG_KEYS = ['declencheur', 'e_sens_in', 'f_trTf', 'f_emaOn_in', 'fenetre', 'f_boOn', 'f_adxMin', 'atr_rel_min',
            'f_maxJour', 'f_detK', 'f_clxOn_in', 'f_clxAge', 'f_feuSeuil']
TRADE_KEYS = ['entree', 'limite_validite', 'x_stopMode_in', 'x_atrK_in', 'x_swL', 'x_swR', 'x_swMarge', 'x_fixPts',
              'x_tpR_in', 'x_trMode_in', 'x_trK', 'x_trAct', 'x_beR', 'x_beTk', 'x_oppArr_in', 'x_oppHei_in', 'x_fin',
              'temps_max_barres']
KEYS = SIG_KEYS + TRADE_KEYS
SIG_FILTER_KEYS = SIG_KEYS + ['x_fin']      # x_fin interdit aussi les entrées après l'heure de fin


def lire_config(path):
    with open(path, 'rb') as f:
        return tomllib.load(f)


def minutes_tf(v):
    return 1440 if v == '1D' else int(v)


class Espace:
    def __init__(self, cfg, tfm):
        self.cfg = cfg
        E = {k: list(v) for k, v in cfg['espace'].items()}
        R = cfg['recherche']
        unites = set(cfg['donnees']['unites_trend'])
        E['f_trTf'] = [v for v in E['f_trTf'] if v == 'aucun' or (minutes_tf(v) > tfm and minutes_tf(v) in unites)]
        if R.get('pine_seulement'):
            E['declencheur'] = [v for v in E['declencheur'] if v != 'rebond_detector']
            E['entree'] = ['marche']
            E['atr_rel_min'] = [0.0]
            E['temps_max_barres'] = [0]
        for k in KEYS:
            if k not in E or not E[k]:
                raise SystemExit('config.toml : paramètre manquant ou vide dans [espace] : %s' % k)
        self.E = E
        self.cat = set(R['parametres_categoriels'])
        self.tfm = tfm

    # ------------------------------------------------------------------ forme canonique
    def pertinent(self, c, k):
        s = c['x_stopMode_in']; t = c['x_trMode_in']
        if k == 'limite_validite': return c['entree'] != 'marche'
        if k == 'x_atrK_in': return s in ('ATR × k', 'Dernier swing + marge')
        if k in ('x_swL', 'x_swR', 'x_swMarge'): return s == 'Dernier swing + marge' or t == 'Sous chaque nouveau swing'
        if k == 'x_fixPts': return s == 'Fixe (points)'
        if k == 'x_trK': return t == 'ATR'
        if k == 'x_trAct': return t != 'Aucun'
        if k == 'x_beTk': return c['x_beR'] > 0
        if k == 'f_clxAge': return bool(c['f_clxOn_in'])
        return True

    def canon(self, c):
        c = dict(c)
        for k in KEYS:
            if not self.pertinent(c, k):
                c[k] = self.E[k][0]
        return c

    def cle(self, c, keys=KEYS):
        return tuple(c[k] for k in keys)

    def depuis_cle(self, key):
        return dict(zip(KEYS, key))

    def pine_ok(self, c):
        return (c['entree'] == 'marche' and float(c['atr_rel_min']) == 0 and int(c['temps_max_barres']) == 0
                and c['declencheur'] != 'rebond_detector')

    # ------------------------------------------------------------------ tirage
    def tirer(self, rng, n_comb, n_sig, n_trade, grille=True):
        sigs, trades = {}, {}
        for _ in range(50 * n_sig):
            if len(sigs) >= n_sig: break
            c = {k: self.E[k][rng.integers(len(self.E[k]))] for k in KEYS}
            c = self.canon(c)
            sigs[self.cle(c, SIG_KEYS)] = c
        for _ in range(50 * n_trade):
            if len(trades) >= n_trade: break
            c = {k: self.E[k][rng.integers(len(self.E[k]))] for k in KEYS}
            c = self.canon(c)
            trades[self.cle(c, TRADE_KEYS)] = c
        S = list(sigs.values()); T = list(trades.values())
        out = {}
        for _ in range(20 * n_comb):
            if len(out) >= n_comb: break
            a = S[rng.integers(len(S))]; b = T[rng.integers(len(T))]
            c = self.canon({**{k: a[k] for k in SIG_KEYS}, **{k: b[k] for k in TRADE_KEYS}})
            out[self.cle(c)] = c
        if grille:
            # grille réduite : chaque déclencheur, sans filtre, avec quelques sorties de référence
            base = {k: self.E[k][0] for k in KEYS}
            for dec in self.E['declencheur']:
                for sens in self.E['e_sens_in']:
                    for st in self.E['x_atrK_in']:
                        for tp in self.E['x_tpR_in']:
                            for hei in self.E['x_oppHei_in']:
                                c = dict(base, declencheur=dec, e_sens_in=sens, x_stopMode_in='ATR × k', x_atrK_in=st,
                                         x_tpR_in=tp, x_oppHei_in=hei, entree='marche', x_trMode_in='Aucun')
                                c = self.canon(c)
                                out[self.cle(c)] = c
        return out

    # ------------------------------------------------------------------ voisins (plateau)
    def voisins(self, c):
        out = []
        for k in KEYS:
            if k in self.cat or not self.pertinent(c, k):
                continue
            L = self.E[k]
            if len(L) < 2 or c[k] not in L: continue
            i = L.index(c[k])
            for j in (i - 1, i + 1):
                if 0 <= j < len(L):
                    v = self.canon(dict(c, **{k: L[j]}))
                    if self.cle(v) != self.cle(c):
                        out.append(v)
        return out

    # ------------------------------------------------------------------ filtres (vectorisés sur les paires)
    def masque(self, U, g, d, c, cache):
        A = U.A
        m = np.ones(len(g), bool)
        s = c['e_sens_in']
        if s == 'Long seulement': m &= d == 1
        elif s == 'Short seulement': m &= d == -1

        if c['f_trTf'] != 'aucun':
            m &= A['trend_%d' % minutes_tf(c['f_trTf'])][g] == d
        if c['f_emaOn_in']:
            m &= A['ema_side'][g] == d
        fen = self.cfg['fenetres'][c['fenetre']]
        if fen:
            key = ('fen', c['fenetre'])
            if key not in cache:
                pm = A['paris_min']; ok = np.zeros(U.N, bool)
                for sess in fen:
                    a, b = sess.split('-'); a = int(a[:2]) * 60 + int(a[2:]); b = int(b[:2]) * 60 + int(b[2:])
                    ok |= ((pm >= a) & (pm < b)) if a < b else ((pm >= a) | (pm < b))
                cache[key] = ok
            m &= cache[key][g]
        if c['f_boOn']:
            m &= ~A['news'][g]
        if c['f_adxMin']:
            with np.errstate(invalid='ignore'):
                m &= A['adx'][g] >= c['f_adxMin']
        if c['atr_rel_min']:
            with np.errstate(invalid='ignore'):
                m &= A['atr_rel'][g] >= c['atr_rel_min']
        if c['f_detK']:
            m &= np.where(d == 1, A['detL'][g], A['detS'][g]) >= c['f_detK']
        if c['f_clxOn_in']:
            frais = (A['clx_age'][g] <= c['f_clxAge']) if c['f_clxAge'] else (A['clx_last'][g] != 0)
            m &= ~((A['clx_last'][g] == -d) & frais)
        if c['f_feuSeuil']:
            th = c['f_feuSeuil'] / 100.0
            with np.errstate(invalid='ignore'):
                m &= np.where(d == 1, A['feu'][g] >= th, (1 - A['feu'][g]) >= th)
        fm = fin_minutes(c['x_fin'])
        if fm is not None:
            m &= A['paris_min_close'][g] < fm
        return m

    def trade_cfg(self, c):
        t = {k: c[k] for k in TRADE_KEYS}
        t['fin_min'] = fin_minutes(c['x_fin'])
        return t


def fin_minutes(v):
    if v in (None, 'aucune'): return None
    h, m = v.split(':')
    return int(h) * 60 + int(m)


# ---------------------------------------------------------------------- traduction Pine
def _b(x): return 'true' if x else 'false'


def bloc_pine(c, cfg, racines):
    """Lignes « variable = valeur // libellé » à recopier dans STRATEGIE_V1.pine (défauts des input) ou à
    saisir dans l'onglet Paramètres de la stratégie."""
    dec = c['declencheur']
    L = []
    add = lambda var, val, lib: L.append('%-14s = %-28s // « %s »' % (var, val, lib))
    add('preset', '"Personnalisé"', 'Préréglage')
    add('e_sens_in', '"%s"' % c['e_sens_in'], 'Sens autorisé')
    add('e_sigOn_in', _b(dec in ('fleche_fort', 'fleche_fort_moyen')), 'Entrée sur flèche Signator')
    add('e_sigNiv_in', '"%s"' % ('Fort + Moyen' if dec == 'fleche_fort_moyen' else 'Fort seulement'), 'Niveau des flèches')
    add('e_heiOn_in', _b(dec == 'heishi'), 'Entrée sur changement de couleur Heishinator')
    add('e_tlOn_in', _b(dec == 'trendline'), 'Entrée sur cassure de trendline (Breakator)')
    add('e_lvlOn_in', _b(dec == 'niveau'), 'Entrée sur cassure de niveau (sessions / Monday)')
    if dec == 'niveau':
        add('e_lvlAs', 'true', 'Niveaux Asie'); add('e_lvlLd', 'true', 'Londres'); add('e_lvlUs', 'true', 'US')
        add('e_lvlMon', 'true', 'Monday')
        add('e_lvlSrc', '"Heiken Ashi (comme l\'indicateur)"', 'Niveaux mesurés sur')
        add('lv_brk', '"Clôture"', 'Cassure de niveau (sessions, Monday) quand')
    add('e_clxOn_in', _b(dec == 'climax'), 'Entrée sur climax (BUY = long, SELL = short)')
    add('f_feuOn_in', _b(c['f_feuSeuil'] > 0), 'Feu de Confluence dans le sens du trade')
    if c['f_feuSeuil']:
        add('f_feuSeuil', str(int(c['f_feuSeuil'])), 'Feu : seuil (%) — ATTENTION proxy 12 voix en Python')
    add('f_trOn_in', _b(c['f_trTf'] != 'aucun'), "TREND d'une unité supérieure dans le sens")
    if c['f_trTf'] != 'aucun':
        add('f_trTf', '"%s"' % c['f_trTf'], 'TREND : unité')
    add('f_emaOn_in', _b(c['f_emaOn_in']), "Clôture du bon côté de l'EMA50 (Moyenator 1)")
    fen = cfg['fenetres'][c['fenetre']]
    add('f_hrOn_in', _b(bool(fen)), 'Fenêtres horaires (heure de Paris)')
    if fen:
        add('f_hr1On_in', 'true', 'Plage 1'); add('f_hr1_in', '"%s"' % fen[0], 'Plage 1 (session)')
        add('f_hr2On_in', _b(len(fen) > 1), 'Plage 2')
        if len(fen) > 1: add('f_hr2', '"%s"' % fen[1], 'Plage 2 (session)')
    add('f_boOn', _b(c['f_boOn']), "Blackout d'annonces sur TOUTES les entrées")
    add('f_adxOn_in', _b(c['f_adxMin'] > 0), 'ADX minimum')
    if c['f_adxMin']: add('f_adxMin', '%.1f' % c['f_adxMin'], 'ADX minimum (valeur)')
    add('f_maxJour', str(int(c['f_maxJour'])), 'Trades maximum par jour (0 = illimité)')
    add('f_detOn_in', _b(c['f_detK'] > 0), "Detector : place jusqu'à la zone opposée")
    if c['f_detK']: add('f_detK', '%.1f' % c['f_detK'], 'Detector : distance minimum (× ATR14)')
    add('f_clxOn_in', _b(c['f_clxOn_in']), 'Climax : ne jamais trader contre le dernier climax')
    if c['f_clxOn_in']: add('f_clxAge', str(int(c['f_clxAge'])), 'Climax : âge maximum')
    add('x_stopMode_in', '"%s"' % c['x_stopMode_in'], 'Stop initial')
    add('x_atrLen', '14', 'ATR (vrais prix) : période')
    if c['x_stopMode_in'] != 'Fixe (points)':
        add('x_atrK_in', '%.1f' % c['x_atrK_in'], 'Stop ATR : k')
    if c['x_stopMode_in'] == 'Dernier swing + marge' or c['x_trMode_in'] == 'Sous chaque nouveau swing':
        add('x_swL', str(c['x_swL']), 'Swing : barres à gauche'); add('x_swR', str(c['x_swR']), 'Swing : barres à droite')
        add('x_swMarge', str(c['x_swMarge']), 'Swing : marge (ticks)')
    if c['x_stopMode_in'] == 'Fixe (points)':
        for r in racines:
            pts = cfg['stop_fixe_points'].get(r, [None, None])[int(c['x_fixPts'])]
            add('x_fixPts', '%s' % pts, 'Stop fixe (points) sur %s' % r)
    add('x_tpOn_in', _b(c['x_tpR_in'] > 0), 'Objectif en R')
    if c['x_tpR_in']: add('x_tpR_in', '%.1f' % c['x_tpR_in'], 'Objectif en R (valeur)')
    add('x_trMode_in', '"%s"' % c['x_trMode_in'], 'Stop suiveur')
    if c['x_trMode_in'] == 'ATR': add('x_trK', '%.1f' % c['x_trK'], 'Suiveur ATR : k')
    if c['x_trMode_in'] != 'Aucun': add('x_trAct', '%.1f' % c['x_trAct'], 'Suiveur actif après (R)')
    add('x_beOn_in', _b(c['x_beR'] > 0), 'Break-even après X R')
    if c['x_beR']:
        add('x_beR', '%.1f' % c['x_beR'], 'Break-even (R)'); add('x_beTk', str(c['x_beTk']), 'Break-even : ticks')
    add('x_oppArr_in', _b(c['x_oppArr_in']), 'Sortie sur flèche Signator opposée (Fort ou Moyen)')
    add('x_oppHei_in', _b(c['x_oppHei_in']), 'Sortie sur changement Heishinator opposé')
    fm = fin_minutes(c['x_fin'])
    add('x_finOn_in', _b(fm is not None), 'Sortie en fin de séance (heure de Paris)')
    if fm is not None:
        add('x_finH', str(fm // 60), 'h'); add('x_finM', str(fm % 60), 'min')
    nonp = []
    if c['entree'] != 'marche':
        nonp.append('entrée à cours limité au milieu de la bougie signal, valable %s barres' % c['limite_validite'])
    if c['atr_rel_min']:
        nonp.append('filtre volatilité : ATR14 / moyenne100(ATR14) >= %.2f' % c['atr_rel_min'])
    if c['temps_max_barres']:
        nonp.append('sortie au temps : %d barres' % c['temps_max_barres'])
    if dec == 'rebond_detector':
        nonp.append('déclencheur « rebond Detector »')
    for x in nonp:
        L.append('// NON DISPONIBLE dans STRATEGIE_V1 (à ajouter) : ' + x)
    return L


def decrire(c):
    """Résumé lisible d'un réglage (une ligne)."""
    p = [c['declencheur']]
    if c['e_sens_in'] != 'Les deux': p.append(c['e_sens_in'].lower())
    if c['f_trTf'] != 'aucun': p.append('TREND %s' % c['f_trTf'])
    if c['f_emaOn_in']: p.append('EMA50')
    if c['fenetre'] != 'aucune': p.append(c['fenetre'])
    if c['f_adxMin']: p.append('ADX>=%g' % c['f_adxMin'])
    if c['atr_rel_min']: p.append('ATRrel>=%g' % c['atr_rel_min'])
    if c['f_maxJour']: p.append('max %d/j' % c['f_maxJour'])
    if c['f_detK']: p.append('Det %g' % c['f_detK'])
    if c['f_clxOn_in']: p.append('pas contre climax')
    if c['f_feuSeuil']: p.append('Feu>=%d' % c['f_feuSeuil'])
    if not c['f_boOn']: p.append('sans blackout')
    p.append('— ' + ('limite %sb' % c['limite_validite'] if c['entree'] != 'marche' else 'marché'))
    s = c['x_stopMode_in']
    p.append('stop ' + ('%gATR' % c['x_atrK_in'] if s == 'ATR × k' else ('swing' if s.startswith('Dernier') else 'fixe#%d' % c['x_fixPts'])))
    if c['x_tpR_in']: p.append('obj %gR' % c['x_tpR_in'])
    if c['x_trMode_in'] == 'ATR': p.append('suiveur %gATR@%gR' % (c['x_trK'], c['x_trAct']))
    elif c['x_trMode_in'] != 'Aucun': p.append('suiveur swing@%gR' % c['x_trAct'])
    if c['x_beR']: p.append('BE %gR' % c['x_beR'])
    if c['x_oppArr_in']: p.append('sortie flèche')
    if c['x_oppHei_in']: p.append('sortie Heishi')
    if c['x_fin'] != 'aucune': p.append('fin %s' % c['x_fin'])
    if c['temps_max_barres']: p.append('max %db' % c['temps_max_barres'])
    return ' '.join(p)
