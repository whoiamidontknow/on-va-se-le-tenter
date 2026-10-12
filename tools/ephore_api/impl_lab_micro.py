"""H5 + details fins : arrondis au tick, comparaisons strictes/larges, decalages d'une barre
(ordre des operations), traitement du volume nul (NQ 1D), ATR/ADX/SMA20 pris sur la barre
precedente."""
import impl_lab_core as C
base=[C.feats(d) for d in C.DATA]

def shift(ds,keys):
    out=[]
    for d in ds:
        e=dict(d)
        for k in keys: e[k]=[None]+d[k][:-1]
        out.append(e)
    return out

def volna(ds):
    """Volume 0 traite comme absent (Pine : na si pas de donnee) -> la conviction volume echoue."""
    out=[]
    for d in ds:
        e=dict(d); n=len(d['c'])
        v=[None if (d['v'][i] is None or d['v'][i]==0) else d['v'][i] for i in range(n)]
        e['v']=[(-1.0 if x is None else x) for x in v]      # -1 => jamais >= vma
        e['vma']=C.sma([0.0 if x is None else x for x in v],20)
        out.append(e)
    return out

def go(name,ds,**tkw):
    tp,fp,fn,errs=C.score(ds,**tkw)
    flag='  <<< MIEUX' if fp+fn<8 else ('  = ref' if (tp,fp,fn)==(153,6,2) else '')
    print(f"  {name:58} {tp:4}/{fp}/{fn}{flag}")
    return tp,fp,fn,errs

print("=== A. comparaisons strictes vs larges ===")
go("reference (vol >= SMA20)",base)
go("vol > SMA20 (strict) -- tue le cas NQ 1D a volume nul ?",base,conv_op='gt')
go("ADX > 18 strict",base,adx_th=18.0000001)
go("dBand > 0.3 strict",base,db_th=0.3000001)

print("\n=== B. volume nul traite comme na (NQ 1D) ===")
go("volume 0 => conviction volume impossible",volna(base))
go("volume 0 => na, ET vol strict",volna(base),conv_op='gt')

print("\n=== C. decalages d'une barre (ordre des operations dans Pine) ===")
for keys,lab in ((['atr'],'ATR[1]'),(['adx'],'ADX[1]'),(['vma'],'SMA20(vol)[1]'),
                 (['e50','e60'],'EMA50/60[1]'),(['dband'],'dBand[1]'),
                 (['atr','adx','vma'],'ATR+ADX+SMA20 tous en [1]')):
    go(f"{lab}",shift(base,keys))

print("\n=== D. arrondis au tick ===")
for name,kw in (('tout OHLC arrondi 0.25',dict(round_tick=True)),):
    tp,fp,fn,_,_=C.run_variant(kw); print(f"  {name:58} {tp:4}/{fp}/{fn}")
# arrondi du seul close
def round_close(ds,q=0.25):
    out=[]
    for d in ds:
        e=dict(d); e['cc']=[round(x/q)*q for x in d['cc']]; out.append(e)
    return out
go("close seul arrondi au tick (test de cote de l'EMA50 + dBand)",round_close(base))

print("\n=== E. combinaisons des deux details qui ont un effet ===")
go("vol strict + ADX strict",base,conv_op='gt',adx_th=18.0000001)
go("volume nul=na + ADX 18",volna(base))
best=go("volume nul=na + dBand strict",volna(base),db_th=0.3000001)
print("\n  erreurs restantes de la meilleure variante ci-dessus :")
for e in best[3]: print("   ",e)
