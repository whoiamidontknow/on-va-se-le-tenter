"""Jeux de données, entrées (événements datés et orientés), filtres (modalités relatives au sens du trade)."""
import datetime
import numpy as np, pandas as pd

CUT = datetime.date(2026, 10, 6)    # jour médian des barres MES : avant = apprentissage, après = validation temps


def sets(df):
    mes, nq = df.group == 'MES', df.group == 'NQ'
    early, late = df.day < CUT, df.day >= CUT
    return {
        'APPR_MES1': mes & early,             # apprentissage : MES, 1re moitié (haussière : NQ ~29700 -> ~31500)
        'VAL_MES2': mes & late,               # validation temps : MES, 2e moitié (chute ~31500 -> ~29850)
        'VAL_NQ1': nq & early,                # validation instrument, même période
        'VAL_NQ2': nq & late,                 # validation instrument ET temps
        'X_MES_avrjul': df.group == 'MES1avr-jul',   # autre période (sans volume)
        'X_API15': df.group == 'API15',       # vrais prix
        'X_API2': df.group == 'API2',
    }


SETS_MAIN = ['APPR_MES1', 'VAL_MES2', 'VAL_NQ1', 'VAL_NQ2']
SETS_X = ['X_MES_avrjul', 'X_API15', 'X_API2']


# ------------------------------------------------------------------ ENTRÉES : sens d (+1/-1) ou 0
def _chg(df, col):
    x = df[col].values; p = df.groupby('sid')[col].shift(1).values
    return np.where((x != p) & ~np.isnan(p.astype(float)) & (x != 0), x, 0)


def entries(df):
    E = {}
    E['sigF'] = df.sigF.values
    E['sigFM'] = np.where(df.sigF != 0, df.sigF, df.sigM).astype(float)
    E['heishi1'] = np.where(df.heishi_age == 1, df.heishi, 0)
    E['heishi2'] = np.where(df.heishi_age == 2, df.heishi, 0)
    E['tl'] = df.tl_break.values
    E['detC'] = df.det_mit.fillna(0).values
    E['detR'] = df.det_rebond.fillna(0).values
    E['clx'] = df.clx.fillna(0).values
    E['sess'] = df.sess_break.values
    E['mon'] = df.mon_break.values
    E['moyX'] = _chg(df, 'moy_pos50')
    E['macdX'] = _chg(df, 'macd_dir')
    E['vidyaX'] = _chg(df, 'vidya')
    E['trend60X'] = _chg(df, 'trend_60')
    return {k: np.asarray(v, float) for k, v in E.items()}


# États directionnels (servent de filtres « aligné / contre » ET de pseudo-entrées « chaque barre dans ce sens »)
DIR = {
    'heishi': lambda d: d.heishi, 'moy_band': lambda d: d.moy_band, 'moy_slope': lambda d: np.sign(d.moy_slope),
    'di': lambda d: d.di, 'dash_tf': lambda d: d.dash_tf, 'trend_tf': lambda d: d.trend_tf,
    'trend_15': lambda d: d.trend_15, 'trend_30': lambda d: d.trend_30, 'trend_60': lambda d: d.trend_60,
    'trend_240': lambda d: d.trend_240, 'trend_D': lambda d: d.trend_D,
    'dash_60': lambda d: d.dash_60, 'dash_240': lambda d: d.dash_240, 'dash_D': lambda d: d.dash_D,
    'heishi_60': lambda d: d.heishi_60, 'heishi_240': lambda d: d.heishi_240, 'heishi_D': lambda d: d.heishi_D,
    'det_in': lambda d: d.det_in, 'sess_AS': lambda d: d.sess_AS_pos, 'sess_LD': lambda d: d.sess_LD_pos,
    'sess_US': lambda d: d.sess_US_pos, 'monday': lambda d: d.mon_pos,
    'piv_mois': lambda d: np.sign(d.piv_mois_P), 'piv_sem': lambda d: np.sign(d.piv_sem_P),
    'rsi50': lambda d: np.sign(d.rsi - 50), 'cci0': lambda d: np.sign(d.cci), 'macd': lambda d: d.macd_dir,
    'yoyo': lambda d: np.sign(d.yoyo), 'bullbear': lambda d: np.sign(d.bullbear), 'vidya': lambda d: d.vidya,
    'feu': lambda d: np.where(d.feu >= 0.6, 1, np.where(d.feu <= 0.4, -1, np.where(d.feu.isna(), np.nan, 0))),
    'clx_recent': lambda d: np.where(d.clx_age_buy <= 10, 1, 0) - np.where(d.clx_age_sell <= 10, 1, 0),
}


def dir_label(s, d):
    """'avec' si l'état va dans le sens d, 'contre' sinon, 'neutre' si 0."""
    s = np.asarray(s, float)
    return np.where(np.isnan(s), None, np.where(s * d > 0, 'avec', np.where(s * d < 0, 'contre', 'neutre')))


def _bins(x, edges, names):
    x = np.asarray(x, float)
    k = np.digitize(x, edges)
    return np.where(np.isnan(x), None, np.array(names, dtype=object)[k])


# Filtres non directionnels ou « signés par d » (modalités)
def nondir(df, d):
    F = {}
    F['seance'] = df.sess.values
    F['adx'] = _bins(df.adx, [20, 25, 35], ['<20', '20-25', '25-35', '>=35'])
    F['vol_rel'] = _bins(df.vol_rel, [0.7, 1.3], ['<0.7', '0.7-1.3', '>=1.3'])
    F['atr_rel'] = _bins(df.atr_rel, [0.8, 1.2], ['<0.8', '0.8-1.2', '>=1.2'])
    F['age_heishi'] = _bins(df.heishi_age, [3, 9, 21], ['1-2', '3-8', '9-20', '>20'])
    F['jour'] = np.array(['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim'], dtype=object)[df.wday.values]
    F['unite'] = df.tf.astype(str).values
    F['ecart_moy'] = _bins(d * df.moy_dist, [-1, 0, 1, 2.5], ['<-1', '-1..0', '0..1', '1..2.5', '>=2.5'])
    F['rsi_sens'] = _bins(d * (df.rsi - 50), [-10, 0, 10, 20], ['<-10', '-10..0', '0..10', '10..20', '>=20'])
    F['yoyo_sens'] = _bins(d * df.yoyo / np.maximum(df.yoyo.abs().groupby(df.sid).transform('median'), 1e-9),
                           [-1, 0, 1, 2], ['<-1', '-1..0', '0..1', '1..2', '>=2'])
    F['dans_zone_det'] = np.where(df.det_in.isna(), None, np.where(df.det_in != 0, 'oui', 'non'))
    tl = np.where(d > 0, -df.tl_res_dist, df.tl_sup_dist)      # distance à la droite « en face » (ATR)
    F['dist_droite'] = _bins(tl, [0.5, 1.5, 4], ['<0.5', '0.5-1.5', '1.5-4', '>=4'])
    F['score_sig'] = _bins(df.sig_score, [50, 65, 80], ['<50', '50-65', '65-80', '>=80'])
    return F
