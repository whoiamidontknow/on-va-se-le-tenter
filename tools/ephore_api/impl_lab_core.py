"""Coeur du laboratoire 'details d'implementation' pour les fleches Signator (groupe 4).

Reimplemente la chaine Signator V8 avec TOUS les choix d'implementation parametrables :
EMA (amorcage), ATR (lissage, 1ere barre), ADX (amorcage, longueurs dissociees),
Heishinator (source, periodes), arrondi au tick, comparaison stricte/large.

Reference a battre : 153 exactes / 6 en trop / 2 manquees (warmup 100, groupe 4, tout niveau).
"""
import csv, glob, os, datetime, math

D = "/Users/jeremk/Ephore/Base 10:10/Ajustements/"
WARM = 100

# ---------- moyennes ----------
def ema_first(x, p):
    """Notre EMA : amorcee a x[0]."""
    a = 2.0/(p+1); out=[x[0]]
    for v in x[1:]: out.append(a*v+(1-a)*out[-1])
    return out

def ema_sma(x, p):
    """ta.ema de Pine : na sur p-1 barres, puis SMA(p) comme graine."""
    a = 2.0/(p+1); out=[None]*len(x)
    if len(x) < p: return out
    out[p-1] = sum(x[:p])/p
    for i in range(p, len(x)): out[i] = a*x[i]+(1-a)*out[i-1]
    return out

def ema(x, p, seed='first'):
    return ema_first(x,p) if seed=='first' else ema_sma(x,p)

def rma(x, p):
    """ta.rma de Pine : graine = SMA(p) des p premieres valeurs NON na, na avant."""
    out=[None]*len(x); s=None; buf=[]
    for i,v in enumerate(x):
        if v is None: continue
        if s is None:
            buf.append(v)
            if len(buf)==p: s=sum(buf)/p
        else: s=(s*(p-1)+v)/p
        out[i]=s
    return out

def rma_nosma(x, p):
    """Variante d'amorcage : graine = 1ere valeur (pas de SMA)."""
    out=[None]*len(x); s=None
    for i,v in enumerate(x):
        if v is None: continue
        s = v if s is None else (s*(p-1)+v)/p
        out[i]=s
    return out

def sma(x, p):
    out=[None]*len(x)
    for i in range(len(x)):
        if i<p-1: continue
        w=x[i-p+1:i+1]
        out[i]=None if any(v is None for v in w) else sum(w)/p
    return out

def ema_series(x, p):
    """EMA tolerante aux None en tete (pour ATR en EMA du TR)."""
    out=[None]*len(x); a=2.0/(p+1); s=None
    for i,v in enumerate(x):
        if v is None: continue
        s = v if s is None else a*v+(1-a)*s
        out[i]=s
    return out

# ---------- chargement ----------
def fl(s): return float(s) if s not in ('',None) else None

def load(f):
    r=list(csv.reader(open(f))); rows=r[1:]
    name=os.path.basename(f); inst='MES' if 'MES' in name else 'NQ'
    tf=name.split(', ')[1].split('_')[0]
    c=lambda i:[fl(x[i]) for x in rows]
    d=dict(inst=inst,tf=tf,file=name,t=[x[0] for x in rows],
           o=c(1),h=c(2),l=c(3),c=c(4),v=c(5),m1=c(34),m2=c(35),
           vraw=[x[5] for x in rows])
    for k,i in (('LF',30),('SF',31),('LM',32),('SM',33)):
        d[k]=[1 if (x[i] not in ('','0')) else 0 for x in rows]
    return d

DATA=[load(f) for f in sorted(glob.glob(D+'*.csv'))]

TICK={'MES':0.25,'NQ':0.25}

# ---------- features parametrables ----------
def feats(d0, ema_seed='first', use_truth_ma=True,
          atr_mode='rma', atr_len=14, tr_first='hl',
          di_len=14, adx_len=14, adx_tr_first='hl', dm_first='zero',
          adx_rma='sma_seed', adx_dx_rma='sma_seed',
          heishi_src='ohlc4', hf=4, hs=32, heishi_seed='first',
          round_tick=False, vol_na_zero=True):
    d=dict(d0); n=len(d['c'])
    o,h,l,c = d['o'][:],d['h'][:],d['l'][:],d['c'][:]
    if round_tick:
        q=TICK[d['inst']]
        rd=lambda a:[round(x/q)*q for x in a]
        o,h,l,c=rd(o),rd(h),rd(l),rd(c)
    v=d['v']
    # --- Heishinator ---
    src={'ohlc4':[(o[i]+h[i]+l[i]+c[i])/4 for i in range(n)],
         'hlc3':[(h[i]+l[i]+c[i])/3 for i in range(n)],
         'hl2':[(h[i]+l[i])/2 for i in range(n)],
         'close':c, 'open':o}[heishi_src]
    ef=ema(src,hf,heishi_seed); es=ema(src,hs,heishi_seed)
    bull=[(None if (ef[i] is None or es[i] is None) else ef[i]>es[i]) for i in range(n)]
    # run : longueur de la serie d'etat courante
    run=[0]*n; prev=None
    for i in range(n):
        if bull[i] is None: run[i]=0; continue
        run[i]= run[i-1]+1 if (prev is not None and bull[i]==prev) else 1
        prev=bull[i]
    # --- EMA50/60 ---
    e50=ema(c,50,ema_seed); e60=ema(c,60,ema_seed)
    if use_truth_ma:
        e50=[a if a is not None else b for a,b in zip(d['m1'],e50)]
        e60=[a if a is not None else b for a,b in zip(d['m2'],e60)]
    # --- True range ---
    tr=[None]*n
    for i in range(1,n): tr[i]=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))
    tr_hl=tr[:]; tr_hl[0]=h[0]-l[0]
    tr_na=tr[:]   # tr[0] reste None
    tr_atr = tr_hl if tr_first=='hl' else tr_na
    if atr_mode=='rma': atr=rma(tr_atr,atr_len)
    elif atr_mode=='sma': atr=sma(tr_atr,atr_len)
    elif atr_mode=='ema': atr=ema_series(tr_atr,atr_len)
    elif atr_mode=='rma_nosma': atr=rma_nosma(tr_atr,atr_len)
    else: raise ValueError(atr_mode)
    # --- ADX ---
    tr_dmi = tr_hl if adx_tr_first=='hl' else tr_na
    up=[None]*n; dn=[None]*n
    for i in range(1,n): up[i]=h[i]-h[i-1]; dn[i]=l[i-1]-l[i]
    if dm_first=='zero': up[0]=0.0; dn[0]=0.0
    pdm=[None if u is None else (u if (u>dn[i] and u>0) else 0.0) for i,u in enumerate(up)]
    mdm=[None if x is None else (x if (x>up[i] and x>0) else 0.0) for i,x in enumerate(dn)]
    R = rma if adx_rma=='sma_seed' else rma_nosma
    R2 = rma if adx_dx_rma=='sma_seed' else rma_nosma
    trs=R(tr_dmi,di_len); ps=R(pdm,di_len); ms=R(mdm,di_len)
    dip=[(100*a/b if (a is not None and b) else None) for a,b in zip(ps,trs)]
    dim=[(100*a/b if (a is not None and b) else None) for a,b in zip(ms,trs)]
    dx=[]
    for a,b in zip(dip,dim):
        if a is None or b is None: dx.append(None)
        else:
            s=a+b; dx.append(abs(a-b)/(s if s!=0 else 1)*100)
    adx=R2(dx,adx_len)
    vma=sma(v,20)
    # --- dBand ---
    dband=[None]*n
    for i in range(n):
        if atr[i] and bull[i] is not None and e50[i] is not None and e60[i] is not None:
            dband[i]=(c[i]-max(e50[i],e60[i]))/atr[i] if bull[i] else (min(e50[i],e60[i])-c[i])/atr[i]
    # --- CQF (disponibilite seulement pour le declenchement) ---
    sc=[None]*n
    for i in range(1,n):
        if atr[i] is None or vma[i] is None or bull[i] is None: continue
        rng=h[i]-l[i]; mt=0.25
        rs=max(rng,mt); br=min(abs(c[i]-o[i])/rs/0.5,1.0)
        cpos=(c[i]-l[i])/rs if bull[i] else (h[i]-c[i])/rs
        aw=(h[i]-c[i])/rs if bull[i] else (c[i]-l[i])/rs
        sS=(br+(1-min(aw/0.35,1))+min(cpos/0.67,1))/3
        sM=min(rng/max(0.5*atr[i],mt),1.0)
        sV=min(v[i]/vma[i],1.0) if vma[i]>0 else 0
        sG=min(abs(o[i]-c[i-1])/max(0.3*atr[i],mt),1.0)
        eng=((c[i]>o[i-1] and o[i]<c[i-1]) if bull[i] else (o[i]>c[i-1] and c[i]<o[i-1])) and h[i]>h[i-1] and l[i]<l[i-1]
        sc[i]=(sS+sM+sV+sG+(1 if eng else 0))/5*100
    d.update(bull=bull,run=run,e50=e50,e60=e60,atr=atr,adx=adx,vma=vma,sc=sc,
             dband=dband,oo=o,hh=h,ll=l,cc=c,tr=tr_atr,dip=dip,dim=dim)
    return d

def trig(d,i,adx_th=18.0,db_th=0.3,vol_k=1.0,run_n=2,conv_op='ge'):
    if d['adx'][i] is None or d['vma'][i] is None or d['dband'][i] is None or d['sc'][i] is None: return None
    b=d['bull'][i]; c=d['cc'][i]
    if d['run'][i]!=run_n: return None
    if not (d['adx'][i]>=adx_th): return None
    if not (c>d['e50'][i] if b else c<d['e50'][i]): return None
    volok = d['v'][i]>=vol_k*d['vma'][i] if conv_op=='ge' else d['v'][i]>vol_k*d['vma'][i]
    if not (d['dband'][i]>=db_th or volok): return None
    return 'L' if b else 'S'

def score(ds, warm=WARM, **kw):
    tp=fp=fn=0; errs=[]
    for d in ds:
        for i in range(warm,len(d['c'])):
            r=trig(d,i,**kw); p=r is not None
            t=bool(d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i])
            tp+=p and t; fp+=p and not t; fn+=t and not p
            if p!=t: errs.append(('FP' if p else 'FN',d['inst'],d['tf'],d['t'][i][:16],i))
    return tp,fp,fn,errs

def run_variant(fkw=None,tkw=None,warm=WARM,data=None):
    fkw=fkw or {}; tkw=tkw or {}
    ds=[feats(d,**fkw) for d in (data or DATA)]
    return score(ds,warm=warm,**tkw)+(ds,)
