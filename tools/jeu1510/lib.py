import csv,glob,os
D="/Users/jeremk/Jeu 15:10/"
def files():
    out=[]
    for f in sorted(glob.glob(D+"*.csv")):
        b=os.path.basename(f); sym=b.split('CME_MINI_')[1][:3]
        tf=b.split(', ')[1].split('_')[0]; out.append((b,sym,tf,f))
    return out
def load(f):
    r=list(csv.reader(open(f))); rows=r[1:]
    def num(x):
        return float(x) if x!='' else None
    return [[x[0]]+[num(v) for v in x[1:]] for x in rows]
