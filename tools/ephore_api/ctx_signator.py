"""Variables de contexte pour les flèches Signator (groupe 4, lot 'Base 10:10/Ajustements').
Ajoute à chaque jeu de données un dict de variables de contexte jamais testées :
heure/fuseau, liquidité horaire, distance aux extrêmes, multi-barres, régime de volatilité.
Usage : import ctx_signator ; ctx_signator.build() -> liste de datasets enrichis.
"""
import sys, datetime, statistics
sys.path.insert(0, '/Users/jeremk/Ephore/on-va-se-le-tenter/tools/ephore_api')
from sim_signator_g4 import all_data, sma, rma, ema, v8

WARM = 100
TFM = {'2':2,'5':5,'15':15,'30':30,'60':60,'240':240,'1D':1440}

def parse(ts):
    # CSV en heure de Paris (offset inclus sauf 1D)
    if len(ts) == 10:
        return datetime.datetime.fromisoformat(ts), True
    return datetime.datetime.fromisoformat(ts), False

def add_ctx(d):
    n = len(d['c']); o,h,l,c,v = d['o'],d['h'],d['l'],d['c'],d['v']
    tfm = TFM[d['tf']]
    hr=[None]*n; mn=[None]*n; wd=[None]*n; dayonly=[False]*n; nyh=[None]*n
    for i,ts in enumerate(d['t']):
        dt, only = parse(ts)
        dayonly[i]=only
        hr[i]=dt.hour; mn[i]=dt.minute; wd[i]=dt.weekday()
        nyh[i]=(dt.hour-6)%24   # Paris -> New York (ecart 6 h)
    # minute du debut de bougie en heure de Paris
    mop=[None if dayonly[i] else hr[i]*60+mn[i] for i in range(n)]
    # --- liquidite horaire : volume / moyenne du meme creneau sur les K jours precedents
    volh=[None]*n
    hist={}
    for i in range(n):
        key = mop[i]
        if key is None or v[i] is None:
            continue
        past = hist.get(key, [])
        if len(past) >= 3:
            m = sum(past[-10:])/len(past[-10:])
            volh[i] = v[i]/m if m > 0 else None
        hist.setdefault(key, []).append(v[i])
    # --- distance aux extremes / position dans le range
    def ext(N):
        hh=[None]*n; ll=[None]*n; pos=[None]*n
        for i in range(n):
            if i < N: continue
            w = range(i-N, i)   # N barres precedentes, barre courante exclue
            hh[i]=max(h[j] for j in w); ll[i]=min(l[j] for j in w)
            rg = hh[i]-ll[i]
            pos[i]=(c[i]-ll[i])/rg if rg>0 else None
        return hh,ll,pos
    E={}
    for N in (10,20,50,100):
        E[N]=ext(N)
    atr=d['atr']
    # distance a l'extreme en ATR
    dext={}
    for N in (10,20,50,100):
        hh,ll,pos = E[N]
        du=[None]*n; dd=[None]*n
        for i in range(n):
            if hh[i] is None or not atr[i]: continue
            du[i]=(hh[i]-c[i])/atr[i]; dd[i]=(c[i]-ll[i])/atr[i]
        dext[N]=(du,dd,pos)
    # --- regime de volatilite : atr / moyenne atr sur N
    volreg={}
    for N in (20,50,100):
        a=sma([x if x is not None else 0 for x in atr],N)
        volreg[N]=[None if (a[i] in (None,0) or atr[i] is None) else atr[i]/a[i] for i in range(n)]
    # range de la barre / atr
    rngatr=[None if not atr[i] else (h[i]-l[i])/atr[i] for i in range(n)]
    # --- multi-barres
    bull=d['bull']
    prevdir=[None]+[1 if c[i-1]>o[i-1] else (-1 if c[i-1]<o[i-1] else 0) for i in range(1,n)]
    # barres depuis derniere flèche de verite / derniere prediction
    sincetruth=[None]*n; sincepred=[None]*n
    lt=None; lp=None
    for i in range(n):
        sincetruth[i]= (i-lt) if lt is not None else 9999
        sincepred[i] = (i-lp) if lp is not None else 9999
        if d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i]: lt=i
        if v8(d,i): lp=i
    # adx pente
    adx=d['adx']
    adxslope=[None]*n
    for i in range(3,n):
        if adx[i] is not None and adx[i-3] is not None: adxslope[i]=adx[i]-adx[i-3]
    d.update(hr=hr,mn=mn,wd=wd,nyh=nyh,mop=mop,dayonly=dayonly,volh=volh,
             dext=dext,volreg=volreg,rngatr=rngatr,prevdir=prevdir,
             sincetruth=sincetruth,sincepred=sincepred,adxslope=adxslope)
    return d

def build():
    return [add_ctx(d) for d in all_data(False)]

def events(ds):
    """retourne (kind, d, i) pour kind in TP/FP/FN"""
    out=[]
    for d in ds:
        for i in range(WARM, len(d['c'])):
            truth = bool(d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i])
            pred = v8(d,i) is not None
            if truth and pred: out.append(('TP',d,i))
            elif truth: out.append(('FN',d,i))
            elif pred: out.append(('FP',d,i))
    return out
