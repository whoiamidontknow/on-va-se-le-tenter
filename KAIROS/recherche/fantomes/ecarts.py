"""Écarts alertes réelles / historique, flux manuels MNQ et MES 15 min (mission DAEMON du 15/11).
Usage : python ecarts.py <KAIROS-data>"""
import glob, os, re, sys
import pandas as pd

R = sys.argv[1]
MOIS = {"janv": 1, "févr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6, "juil": 7, "août": 8, "sept": 9, "oct": 10,
        "nov": 11, "déc": 12}
FLUX = {"MNQ15": ("CME_MINI:MNQ1!, 15m", 5884297809, "MNQ1!"), "MES15": ("CME_MINI:MES1!, 15m", 5886471945, "MES1!")}

# ---------- journal ----------
logs = []
for f in glob.glob(os.path.join(glob.escape(R), "**", "TradingView_Alerts_Log*.csv"), recursive=True):
    d = pd.read_csv(f)
    d["fichier"] = f
    logs.append(d)
L = pd.concat(logs).drop_duplicates(["ID de l'alerte", "Heure", "Description"])
L["t"] = pd.to_datetime(L["Heure"]).dt.tz_convert("Europe/Paris").dt.tz_localize(None)
L = L.sort_values("t", kind="stable")
FIN_JOURNAL = L["t"].max()


def num(txt, motif):
    m = re.search(motif, txt)
    return float(m.group(1).replace(",", "").replace(" ", "").replace(" ", "")) if m else None


def direct(flux):
    tk, aid, sym = FLUX[flux]
    s = L[L["ID de l'alerte"] == aid]
    trades, ouvert, orphelins = [], None, []
    for a in s.itertuples():
        d = str(a.Description)
        if "au marché maintenant" in d:
            ouvert = dict(entree=a.t, sens="L" if "ACHAT" in d else "S", etiq="GODLIKE" if "GODLIKE" in d else "56 seul",
                          px=num(d, r"Entrée ≈ ([\d.,]+)"), stop=num(d, r"Stop ([\d.,]+)"), obj=num(d, r"Objectif ([\d.,]+)"),
                          sortie=None, raison=None, pnl=None)
            trades.append(ouvert)
        elif "trade terminé" in d or "FERMER" in d:
            raison = ("objectif" if "OBJECTIF" in d else "stop") if "trade terminé" in d else \
                ("fin de fenêtre" if "fin de la fenêtre" in d else "temps")
            pnl = num(d, r"P&L ≈? ?(-?[\d.,  ]+) \$")
            if ouvert is None:
                orphelins.append(dict(t=a.t, raison=raison, pnl=pnl, txt=d[:90]))
            else:
                ouvert.update(sortie=a.t, raison=raison, pnl=pnl)
                ouvert = None
    return pd.DataFrame(trades), orphelins, s["t"].min(), s["t"].max()


# ---------- exports ----------
def plage(f):
    p = pd.read_excel(f, "Propriétés", header=None)
    for _, r in p.iterrows():
        if str(r.iloc[0]).startswith("Plage de backtesting"):
            d = [pd.Timestamp(int(a), MOIS[m], int(j), int(h), int(mi)) for j, m, a, h, mi in
                 re.findall(r"(\d{1,2}) (\w+)\.? (\d{4}), (\d{2}):(\d{2})", str(r.iloc[1])) if m in MOIS]
            return d[0], d[1]


def trades_export(f):
    t = pd.read_excel(f, "Trades")
    t["dt"] = pd.to_datetime(t["Date et heure"], errors="coerce")
    e = t[t["Type"].str.startswith("Entrer")].set_index("Numéro de trade")
    x = t[t["Type"].str.startswith("Sortir")].set_index("Numéro de trade")
    out = pd.DataFrame({"entree": e["dt"], "sens": e["Signal"].str[0], "etiq": e["Signal"].map(lambda s: "GODLIKE" if "GODLIKE" in s else "56 seul"),
                        "px": e["Prix USD"], "sortie": x["dt"].reindex(e.index), "sig_sortie": x["Signal"].reindex(e.index).astype(str),
                        "px_sortie": x["Prix USD"].reindex(e.index), "pnl": e["P&L net USD"], "qte": e["Taille (qté)"]})
    out["raison"] = out["sig_sortie"].map(lambda s: "objectif" if s.startswith("Obj") else "stop" if s.startswith("Stop")
                                          else "temps" if s.startswith("Temps") else "fin de fenêtre" if ("séance" in s or "fenêtre" in s) else "en cours" if (s == "nan" or "Ouverture" in s) else s)
    return out.dropna(subset=["entree"]).reset_index(drop=True)


EXP = {k: [] for k in FLUX}
for f in sorted(glob.glob(os.path.join(glob.escape(R), "**", "Strat5669*.xlsx"), recursive=True)):
    if "slcourtoupas" in f:
        continue   # expérience « SL court ou pas » du 24/10, autres réglages
    for k, (_, _, sym) in FLUX.items():
        if sym in os.path.basename(f):
            t = trades_export(f)
            if not (t["entree"].dt.minute % 15 == 0).all():
                continue   # 5 min / 2 min : autre flux
            deb, fin = plage(f)
            jour = re.search(r"_(\d{4}-\d{2}-\d{2})_", f).group(1)
            EXP[k].append(dict(f=f, nom=os.path.relpath(f, R), jour=jour, deb=deb, fin=fin, t=t))


MARGE = 7   # jours d'historique avant le trade : en début de plage, étiquette et état ne sont pas fiables


def export_pour(k, quand):
    c = [e for e in EXP[k] if e["deb"] <= quand <= e["fin"]]
    c = [e for e in c if e["deb"] <= quand - pd.Timedelta(days=MARGE)] or c
    return max(c, key=lambda e: (e["fin"], e["jour"], len(e["t"]))) if c else None


def proche(t, quand, sens, tol=15):
    m = t[((t["entree"] - quand).abs() <= pd.Timedelta(minutes=tol)) & (t["sens"] == sens)]
    return None if m.empty else m.iloc[0]


# ---------- 1. écarts direct / historique ----------
lignes, stats = [], {}
for k in FLUX:
    dv, orph, t0, t1 = direct(k)
    print(f"\n===== {k} : alerte active (messages) du {t0:%d/%m %H:%M} au {t1:%d/%m %H:%M} ; journal jusqu'au {FIN_JOURNAL:%d/%m %H:%M}")
    print("  exports :", [(e["nom"].split("/")[0], f"{e['deb']:%d/%m/%y}", f"{e['fin']:%d/%m %H:%M}", len(e["t"])) for e in EXP[k]])
    vus = set()
    for tr in dv.itertuples():
        e = export_pour(k, tr.entree)
        if e is None:
            lignes.append((k, tr.entree, tr.sens, tr.etiq, tr.raison, tr.pnl, "e", "aucun export ne couvre", "certaine", None))
            continue
        h = proche(e["t"], tr.entree, tr.sens)
        if h is None:
            lignes.append((k, tr.entree, tr.sens, tr.etiq, tr.raison, tr.pnl, "b", f"absent de {e['nom'].split('/')[0]}", "certaine", None))
            continue
        vus.add((e["nom"], h["entree"]))
        diffs = []
        if h["etiq"] != tr.etiq: diffs.append(f"étiquette {tr.etiq}→{h['etiq']}")
        if h["entree"] != tr.entree.floor("min"): diffs.append(f"heure {tr.entree:%H:%M}→{h['entree']:%H:%M}")
        if tr.px and abs(h["px"] - tr.px) > (2.0 if k == "MNQ15" else 0.75): diffs.append(f"prix {tr.px}→{h['px']}")
        if tr.raison and h["raison"] != tr.raison: diffs.append(f"sortie {tr.raison}→{h['raison']}")
        if tr.pnl is not None and pd.notna(tr.pnl) and abs(h["pnl"] - tr.pnl) > 15: diffs.append(f"P&L {tr.pnl:+.0f}→{h['pnl']:+.0f}")
        lignes.append((k, tr.entree, tr.sens, tr.etiq, tr.raison, tr.pnl, "d" if diffs else "=", "; ".join(diffs), "certaine", h["pnl"]))
    # trades de l'historique sans alerte
    for e in EXP[k]:
        for h in e["t"].itertuples():
            if export_pour(k, h.entree) is not e or h.entree < pd.Timestamp("2026-10-15"):
                continue
            if (e["nom"], h.entree) in vus or proche(dv, h.entree, h.sens) is not None:
                continue
            o = [x for x in orph if pd.notna(h.sortie) and abs((x["t"] - h.sortie).total_seconds()) <= 15 * 60 + 60]
            if h.entree < t0:
                cause, cert, note = "a", "certaine", f"avant le 1er message de l'alerte ({t0:%d/%m %H:%M})"
            elif h.entree > t1:
                cause, cert, note = "a ou c", "indéterminée", f"après le dernier message de l'alerte ({t1:%d/%m %H:%M})"
            else:
                cause, cert, note = "c", "élevée", "alerte active avant et après"
            if o:
                note += f" ; SORTIE alertée sans entrée à {o[0]['t']:%H:%M} ({o[0]['raison']} {o[0]['pnl']})"
            lignes.append((k, h.entree, h.sens, h.etiq, h.raison, None, cause, note, cert, h.pnl))
    stats[k] = (dv, orph, t0, t1)
    for x in orph:
        print("  sortie orpheline :", x)

df = pd.DataFrame(lignes, columns=["flux", "entree", "sens", "etiq", "res_alerte", "pnl_alerte", "cause", "detail", "certitude", "pnl_hist"])
df = df.sort_values(["entree", "flux"])
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 90)
def statut(k, quand, sens):
    out = []
    for e in sorted(EXP[k], key=lambda e: e["jour"]):
        if e["deb"] + pd.Timedelta(days=MARGE) <= quand <= e["fin"]:
            h = proche(e["t"], quand, sens)
            out.append(f"{e['jour'][8:]}/{e['jour'][5:7]}:" + ("absent" if h is None else f"{h['etiq'][:2]}/{h['raison'][:3]}"))
    return " ".join(out)


df["exports"] = [statut(r.flux, r.entree, r.sens) if r.cause not in ("=", "a") else "" for r in df.itertuples()]
df.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecarts.csv"), index=False)
print("\n" + df.drop(columns=["certitude"]).assign(entree=df.entree.dt.strftime("%d/%m %H:%M")).to_string(index=False))

# ---------- 3. synthèse ----------
print("\n===== SYNTHÈSE (fenêtre : 1er message de l'alerte → 13/11 22:45)")
for k, (dv, orph, t0, t1) in stats.items():
    a = df[(df.flux == k) & df.pnl_alerte.notna()]
    al = dv
    connus = al[al.pnl.notna()]
    # P&L des sorties au temps : l'alerte (version du 20/10) n'en donne pas → pris dans l'historique si le trade y est
    al2 = al.copy()
    for i, tr in al2.iterrows():
        if pd.isna(tr.pnl):
            m = df[(df.flux == k) & (df.entree == tr.entree) & df.pnl_hist.notna()]
            if len(m): al2.loc[i, "pnl"] = m.pnl_hist.iloc[0]
    c2 = al2[al2.pnl.notna()]
    hist = []
    for e in EXP[k]:
        for h in e["t"].itertuples():
            if export_pour(k, h.entree) is e and t0 <= h.entree <= pd.Timestamp("2026-11-13 22:45"):
                hist.append(h)
    hist = pd.DataFrame(hist)
    n_ec = (df[(df.flux == k) & (df.entree >= t0)].cause != "=").sum()
    print(f"  {k} DÉTAIL : écarts par cause", df[(df.flux == k) & (df.entree >= t0)].cause.value_counts().to_dict())
    for nom, s in (("tel qu'alerté (P&L d'alerte, sinon historique)", c2), ("tel que l'historique le raconte", hist[hist.raison != "en cours"])):
        print(f"  {k} {nom:50} {len(s):3} trades · {100 * (s.pnl > 0).mean():5.1f} % · net {s.pnl.sum():+8,.0f} $")
    for nom, s in (("  dont GODLIKE alerté", c2[c2.etiq == "GODLIKE"]), ("  dont GODLIKE historique", hist[(hist.etiq == "GODLIKE") & (hist.raison != "en cours")])):
        print(f"  {k} {nom:50} {len(s):3} trades · {100 * (s.pnl > 0).mean():5.1f} % · net {s.pnl.sum():+8,.0f} $")
    print(f"  {k} alertes d'entrée {len(al)} (P&L inconnu : {al2.pnl.isna().sum()}) · écarts {n_ec} → {100 * n_ec / len(al):.0f} pour 100 alertes")

# ---------- 2. exports successifs ----------
print("\n===== EXPORTS SUCCESSIFS (période commune, un jour de recul après le début le plus tardif)")
for k in FLUX:
    ex = sorted(EXP[k], key=lambda e: (e["jour"], e["fin"]))
    for i, a in enumerate(ex):
        for b in ex[i + 1:]:
            if b["jour"] == a["jour"]:
                continue
            deb = max(a["deb"], b["deb"]) + pd.Timedelta(days=1)
            fin = min(a["fin"], b["fin"])
            if fin <= deb:
                continue
            ta = a["t"][(a["t"].entree >= deb) & (a["t"].entree <= fin) & (a["t"].raison != "en cours")]
            tb = b["t"][(b["t"].entree >= deb) & (b["t"].entree <= fin) & (b["t"].raison != "en cours")]
            ka = {(r.entree, r.sens): r for r in ta.itertuples()}
            kb = {(r.entree, r.sens): r for r in tb.itertuples()}
            dis = sorted(set(ka) - set(kb)); app = sorted(set(kb) - set(ka))
            chg = []
            for kk in set(ka) & set(kb):
                x, y = ka[kk], kb[kk]
                d = []
                if x.etiq != y.etiq: d.append(f"étiquette {x.etiq}→{y.etiq}")
                if x.raison != y.raison: d.append(f"sortie {x.raison}→{y.raison}")
                if abs(x.pnl / x.qte - y.pnl / y.qte) > 1: d.append(f"P&L/contrat {x.pnl / x.qte:+.0f}→{y.pnl / y.qte:+.0f}")
                if d: chg.append((kk, d))
            print(f"  {k} {a['nom'].split('/')[0]:>14} ({a['jour'][5:]}) vs {b['nom'].split('/')[0]:>14} ({b['jour'][5:]}) "
                  f"| {deb:%d/%m}→{fin:%d/%m %H:%M} | {len(ta)} vs {len(tb)} trades | disparus {len(dis)} · apparus {len(app)} · changés {len(chg)}")
            for kk in dis: print(f"      disparu  {kk[0]:%d/%m %H:%M} {kk[1]} {ka[kk].etiq} {ka[kk].raison} {ka[kk].pnl:+.0f}")
            for kk in app: print(f"      apparu   {kk[0]:%d/%m %H:%M} {kk[1]} {kb[kk].etiq} {kb[kk].raison} {kb[kk].pnl:+.0f}")
            for kk, d in sorted(chg): print(f"      changé   {kk[0]:%d/%m %H:%M} {kk[1]} : {', '.join(d)}")
