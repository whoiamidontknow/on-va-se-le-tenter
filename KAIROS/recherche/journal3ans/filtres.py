import numpy as np
def f40(d):
    ok=((d.sens==1)&(d.F>=5)&(d.I>=3))|((d.sens==-1)&(d.F<=-5)&(d.I<=-3))
    ok&=d.trig.str.contains('[FMHTNC]')
    ok&=(d.z>=1.5)
    return d[ok]
def f44(d):
    d=f40(d); return d[~d.h.isin([8,9])]
