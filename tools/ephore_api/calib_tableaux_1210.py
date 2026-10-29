#!/usr/bin/env python3
# Calibration des tableaux Ephore - screen MES 15m du 2026-10-12 14:11 Paris
# Donnees : /Users/jeremk/ERGON/Lun12:10/  (OHLC deja en Heiken Ashi, PAS de volume)
import csv, glob, os, math, itertools, sys

DIR = '/Users/jeremk/ERGON/Lun12:10'
CUT = '2026-10-12T14:15:00+02:00'   # rien apres l'heure du screen (14:11:41 Paris)

FILES = {
 '2':   'CME_MINI_MESZ2026, 2_4720b.csv',
 '5':   'CME_MINI_MESZ2026, 5_2eb65.csv',
 '15':  'CME_MINI_MESZ2026, 15_7f431.csv',
 '30':  'CME_MINI_MESZ2026, 30_c4747.csv',
 '60':  'CME_MINI_MESZ2026, 60_f32cb.csv',
 '240': 'CME_MINI_MESZ2026, 240_5b64a.csv',
 '1D':  'CME_MINI_MESZ2026, 1D_f6b91.csv',
}

def load(fn):
    rows = list(csv.DictReader(open(os.path.join(DIR, fn))))
    out = []
    for r in rows:
        try:
            o, h, l, c = float(r['open']), float(r['high']), float(r['low']), float(r['close'])
        except Exception:
            continue
        m1 = r.get('Moyenator 1') or ''
        out.append(dict(t=r['time'], o=o, h=h, l=l, c=c,
                        m1=float(m1) if m1 else None))
    return [x for x in out if x['t'] <= CUT]

def ema(v, n):
    k = 2.0/(n+1); out=[]; e=None
    for x in v:
        e = x if e is None else x*k + e*(1-k)
        out.append(e)
    return out

def sma(v, n):
    out=[]; s=0.0
    for i,x in enumerate(v):
        s+=x
        if i>=n: s-=v[i-n]
        out.append(s/min(i+1,n))
    return out

def rma(v, n):
    out=[]; e=None
    for i,x in enumerate(v):
        if i < n-1: out.append(None); continue
        if e is None: e = sum(v[:n])/n
        else: e = (e*(n-1)+x)/n
        out.append(e)
    return out

def rsi(c, n=14):
    g=[0.0]; ls=[0.0]
    for i in range(1,len(c)):
        d=c[i]-c[i-1]; g.append(max(d,0.0)); ls.append(max(-d,0.0))
    ag, al = rma(g,n), rma(ls,n)
    return [None if ag[i] is None else (100.0 if al[i]==0 else 100-100/(1+ag[i]/al[i])) for i in range(len(c))]

def cci(h,l,c,n=20):
    tp=[(h[i]+l[i]+c[i])/3 for i in range(len(c))]
    ma=sma(tp,n); out=[]
    for i in range(len(c)):
        w=tp[max(0,i-n+1):i+1]
        md=sum(abs(x-ma[i]) for x in w)/len(w)
        out.append(0.0 if md==0 else (tp[i]-ma[i])/(0.015*md))
    return out

def atr(h,l,c,n=14):
    tr=[h[0]-l[0]]
    for i in range(1,len(c)):
        tr.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    return rma(tr,n), tr

def adx(h,l,c,dilen=14,adxlen=14):
    n=len(c); pdm=[0.0]; ndm=[0.0]; tr=[h[0]-l[0]]
    for i in range(1,n):
        up=h[i]-h[i-1]; dn=l[i-1]-l[i]
        pdm.append(up if (up>dn and up>0) else 0.0)
        ndm.append(dn if (dn>up and dn>0) else 0.0)
        tr.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    trr=rma(tr,dilen); pr=rma(pdm,dilen); nr=rma(ndm,dilen)
    pdi=[]; ndi=[]; dx=[]
    for i in range(n):
        if trr[i] in (None,0) or pr[i] is None:
            pdi.append(None); ndi.append(None); dx.append(None); continue
        p=100*pr[i]/trr[i]; m=100*nr[i]/trr[i]
        pdi.append(p); ndi.append(m)
        dx.append(0.0 if p+m==0 else 100*abs(p-m)/(p+m))
    dxv=[x for x in dx if x is not None]
    adxv=rma(dxv,adxlen)
    out=[None]*(n-len(adxv))+adxv
    return out,pdi,ndi

def macd(c, f=12, s=26, sig=9):
    ef, es = ema(c,f), ema(c,s)
    line=[ef[i]-es[i] for i in range(len(c))]
    sg=ema(line,sig)
    return line, sg, [line[i]-sg[i] for i in range(len(c))]

def supertrend(h,l,c,n=10,mult=3.0):
    a,_=atr(h,l,c,n)
    st=[None]*len(c); dirn=[None]*len(c); fu=fl=None
    for i in range(len(c)):
        if a[i] is None: continue
        src=(h[i]+l[i])/2
        ub=src+mult*a[i]; lb=src-mult*a[i]
        if fu is None: fu,fl=ub,lb; dirn[i]=1; st[i]=lb; continue
        fl = lb if (lb>fl or c[i-1]<fl) else fl
        fu = ub if (ub<fu or c[i-1]>fu) else fu
        pd = dirn[i-1] if dirn[i-1] else 1
        if pd==1 and c[i]<fl: d=-1
        elif pd==-1 and c[i]>fu: d=1
        else: d=pd
        dirn[i]=d; st[i]= fl if d==1 else fu
    return st,dirn

def compute(tf):
    b = load(FILES[tf])
    c=[x['c'] for x in b]; h=[x['h'] for x in b]; l=[x['l'] for x in b]; o=[x['o'] for x in b]
    ohlc4=[(o[i]+h[i]+l[i]+c[i])/4 for i in range(len(c))]
    i=len(c)-1
    e50,e60,e200,e20,e9,e21 = ema(c,50),ema(c,60),ema(c,200),ema(c,20),ema(c,9),ema(c,21)
    s10,s20,s50 = sma(c,10),sma(c,20),sma(c,50)
    r=rsi(c,14); cc20=cci(h,l,c,20); cc30=cci(h,l,c,30)
    a14,tr=atr(h,l,c,14)
    ax,pdi,ndi=adx(h,l,c,14,14)
    ml,ms,mh=macd(c)
    st,sd=supertrend(h,l,c)
    hei4,hei32=ema(ohlc4,4),ema(ohlc4,32)
    return dict(tf=tf,t=b[i]['t'],n=len(b),
        close=c[i],open=o[i],high=h[i],low=l[i],
        m1_csv=b[i]['m1'], ema50=e50[i], ema60=e60[i], ema200=e200[i], ema20=e20[i],
        ema9=e9[i], ema21=e21[i], sma10=s10[i], sma20=s20[i], sma50=s50[i],
        rsi=r[i], cci20=cc20[i], cci30=cc30[i], atr14=a14[i],
        adx=ax[i], pdi=pdi[i], ndi=ndi[i],
        macd=ml[i], macdsig=ms[i], macdhist=mh[i],
        st_dir=sd[i], hei=hei4[i]-hei32[i],
        yoyo=(c[i]-s10[i])/s10[i]*100.0,
        dist_e50_atr=(c[i]-e50[i])/a14[i] if a14[i] else None)

if __name__=='__main__':
    res={tf:compute(tf) for tf in FILES}
    for tf in ['2','5','15','30','60','240','1D']:
        d=res[tf]
        print('--- TF %-4s %s  (%d barres)' % (tf,d['t'],d['n']))
        print('    close %.4f  EMA50 %.4f (CSV %.4f)  EMA60 %.4f' % (d['close'],d['ema50'],d['m1_csv'] or -1,d['ema60']))
        print('    RSI %.2f  CCI20 %.2f  CCI30 %.2f  ADX %.2f  +DI %.2f  -DI %.2f  ATR %.3f' %
              (d['rsi'],d['cci20'],d['cci30'],d['adx'] or -1,d['pdi'],d['ndi'],d['atr14']))
        print('    MACD %.3f sig %.3f hist %.3f | ST dir %s | Heishi %.3f | YoYo %.3f%%' %
              (d['macd'],d['macdsig'],d['macdhist'],d['st_dir'],d['hei'],d['yoyo']))

    # ---- recherche des 4 sous-tests du STRENGTH ----
    OBS = {'5':(False,0.75), '15':(False,0.25), '60':(True,0.50), '240':(True,0.75), '1D':(True,1.00)}
    def tests(d):
        return {
          'close>EMA50'  : d['close']>d['ema50'],
          'EMA50>EMA60'  : d['ema50']>d['ema60'],
          'close>EMA200' : d['close']>d['ema200'],
          'close>EMA20'  : d['close']>d['ema20'],
          'EMA9>EMA21'   : d['ema9']>d['ema21'],
          'close>SMA10'  : d['close']>d['sma10'],
          'close>SMA20'  : d['close']>d['sma20'],
          'close>SMA50'  : d['close']>d['sma50'],
          'RSI>50'       : d['rsi']>50,
          'RSI>45'       : d['rsi']>45,
          'RSI>55'       : d['rsi']>55,
          'CCI20>0'      : d['cci20']>0,
          'CCI30>0'      : d['cci30']>0,
          'CCI20>100'    : d['cci20']>100,
          'MACD>sig'     : d['macd']>d['macdsig'],
          'MACD>0'       : d['macd']>0,
          'hist>0'       : d['macdhist']>0,
          'ST=bull'      : d['st_dir']==1,
          'Heishi'       : d['hei']>0,
          'HAclose>open' : d['close']>d['open'],
          '+DI>-DI'      : d['pdi']>d['ndi'],
          'ADX>=18'      : (d['adx'] or 0)>=18,
          'ADX>=25'      : (d['adx'] or 0)>=25,
        }
    T={tf:tests(res[tf]) for tf in OBS}
    names=sorted(T['15'].keys())
    print('\n=== booleens par TF ===')
    print('%-14s %s' % ('test',' '.join('%6s'%tf for tf in OBS)))
    for nm in names:
        print('%-14s %s' % (nm,' '.join('%6s'%('B' if T[tf][nm] else '.') for tf in OBS)))

    print('\n=== combinaisons de 4 tests reproduisant 75/25/50/75/100 (5/15/60/240/1D) ===')
    hits=0
    for combo in itertools.combinations(names,4):
        ok=True
        for tf,(bull,target) in OBS.items():
            n=sum(1 for nm in combo if T[tf][nm]==bull)   # tests d'accord avec la tendance
            if abs(n/4.0-target)>1e-9: ok=False; break
        if ok:
            hits+=1
            if hits<=60: print('  AGREE :', ' + '.join(combo))
    print('  total (lecture "accord avec la tendance") :',hits)

    hits2=0
    for combo in itertools.combinations(names,4):
        ok=True
        for tf,(bull,target) in OBS.items():
            n=sum(1 for nm in combo if T[tf][nm])          # tests haussiers bruts
            if abs(n/4.0-target)>1e-9: ok=False; break
        if ok:
            hits2+=1
            if hits2<=60: print('  BRUT  :', ' + '.join(combo))
    print('  total (lecture "pression acheteuse brute") :',hits2)
