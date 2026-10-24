"""Journal des trades VÉCUS EN DIRECT (Strat5669 / Bot5669), reconstruit depuis le journal d'alertes TradingView,
puis comparé à l'historique recalculé (export xlsx) pour compter les fantômes.

Le graphique recalcule tout à chaque rechargement : un trade pris en direct peut disparaître ou changer. Le journal
d'alertes, lui, ne bouge plus : c'est la seule trace de ce qui a vraiment été signalé. Les statistiques « en direct »
ci-dessous sont donc celles qui comptent pour juger la méthode ; celles du backtest sont un repère.

Usage : uv run --with pandas --with openpyxl python verif_fantomes.py <dossier Strat-Botting-data> [--csv sortie.csv]
Cherche récursivement les TradingView_Alerts_Log*.csv et les exports Strat5669 / Stratégie 56 / Bot5669.
"""
import glob, os, re, sys
import pandas as pd

args = [a for a in sys.argv[1:] if not a.startswith("--")]
racine = args[0] if args else "."
sortie = sys.argv[sys.argv.index("--csv") + 1] if "--csv" in sys.argv else None
verrou = sys.argv[sys.argv.index("--verrou") + 1] if "--verrou" in sys.argv else None
suivi = sys.argv[sys.argv.index("--suivi") + 1] if "--suivi" in sys.argv else None


def fichiers(motif):
    return glob.glob(os.path.join(glob.escape(racine), "**", motif), recursive=True)


def nombre(txt, motif):
    m = re.search(motif, txt)
    return float(m.group(1).replace(",", "").replace(" ", "").replace(" ", "")) if m else None


# --- 1. alertes ------------------------------------------------------------------------------------------------
logs = pd.concat([pd.read_csv(f) for f in fichiers("TradingView_Alerts_Log*.csv")])
logs = logs.drop_duplicates(["ID de l'alerte", "Heure", "Description"])
logs["t"] = pd.to_datetime(logs["Heure"]).dt.tz_convert("Europe/Paris").dt.tz_localize(None)
logs["sym"] = logs["Ticker"].str.split(",").str[0].str.split(":").str[-1]
logs["tf"] = logs["Ticker"].str.split(", ").str[1]
logs = logs.sort_values("t", kind="stable")
# nom de la stratégie de chaque alerte (lu dans les messages « ordre … effectué » qui commencent par le nom)
STRATS = ("correctifstest", "Bot5669", "Strat5669", "Stratégie 56")
strat_id = {}
for _, a in logs.iterrows():
    for n in STRATS:
        if str(a["Description"]).startswith(n):
            strat_id[a["ID de l'alerte"]] = n

trades, ouverts = [], {}
for _, a in logs.iterrows():
    d, cle = str(a["Description"]), (a["ID de l'alerte"], a["sym"])
    if "au marché maintenant" in d and re.search("GODLIKE|56 seul", d):
        ouverts[cle] = dict(id=a["ID de l'alerte"], strat=strat_id.get(a["ID de l'alerte"], "Strat5669"), entree=a.t, sym=a.sym, tf=a.tf, sens="L" if "ACHAT" in d else "S",
                            etiq="GODLIKE" if "GODLIKE" in d else "56 seul",
                            px=nombre(d, r"Entrée ≈ ([\d.,]+)"), stop=nombre(d, r"Stop ([\d.,]+)"),
                            obj=nombre(d, r"Objectif ([\d.,]+)"), sortie=None, raison=None, px_sortie=None, pnl=None)
        trades.append(ouverts[cle])
    elif cle in ouverts and ("trade terminé" in d or "FERMER la position" in d):
        tr = ouverts.pop(cle)
        tr["sortie"] = a.t
        if "trade terminé" in d:
            tr["raison"] = "objectif" if "OBJECTIF" in d else "stop"
            tr["px_sortie"] = nombre(d, r"touché à ([\d.,]+)")
            tr["pnl"] = nombre(d, r"P&L (-?[\d.,  ]+) \$")
        else:
            tr["raison"] = "fin de fenêtre" if "fin de la fenêtre" in d else "temps"
            tr["px_sortie"] = nombre(d, r"prix ≈ ([\d.,]+)")
            tr["pnl"] = nombre(d, r"P&L ≈ (-?[\d.,  ]+) \$")

# --- 2. historique recalculé -------------------------------------------------------------------------------------
exports = {}
for f in fichiers("*.xlsx"):
    nom = os.path.basename(f)
    m = re.search(r"(MNQ1!|MES1!|BTCUSD|BTC1!|MBT1!)", nom)
    st = re.match(r"(correctifstest|Strat5669|Stratégie_56|Bot5669)", nom)
    if not m or not st:
        continue
    st = {"Stratégie_56": "Strat5669"}.get(st.group(1), st.group(1))
    tf = "5m" if (os.sep + "5min" + os.sep in f or nom.startswith("Bot")) else "15m"
    t = pd.read_excel(f, "Trades")
    t["Date et heure"] = pd.to_datetime(t["Date et heure"])
    exports.setdefault((st, m.group(1), tf), []).append((t["Date et heure"].max(), t))

for tr in trades:
    couverts = [t for mx, t in exports.get((tr["strat"] if tr["strat"] != "Stratégie 56" else "Strat5669", tr["sym"], tr["tf"]), []) if tr["entree"] <= mx]
    tr["historique"], tr["pnl_hist"] = "pas encore exporté", None
    if not couverts:
        continue
    t = max(couverts, key=len)
    e = t[t["Type"].str.startswith("Entrer") & ((t["Date et heure"] - tr["entree"]).abs() <= pd.Timedelta(minutes=15))]
    e = e[e["Signal"].str.startswith(tr["sens"])]
    if e.empty:
        tr["historique"] = "ABSENT (fantôme)"
        continue
    r = e.iloc[0]
    etiq = "GODLIKE" if "GODLIKE" in r["Signal"] else "56 seul"
    tr["historique"] = "présent" if etiq == tr["etiq"] else f"présent, devenu « {etiq} »"
    tr["pnl_hist"] = r["P&L net USD"]
    if tr["pnl"] is None and tr["sortie"] is not None:
        tr["pnl"], tr["raison"] = r["P&L net USD"], tr["raison"] + " (P&L de l'historique)"

# --- 3. affichage ------------------------------------------------------------------------------------------------
df = pd.DataFrame(trades)
if df.empty:
    sys.exit("Aucune alerte d'entrée Strat5669 trouvée.")
print("TRADES SIGNALÉS EN DIRECT (journal d'alertes)\n")
for tr in trades:
    pnl = "en cours" if tr["sortie"] is None else ("P&L ?" if tr["pnl"] is None else f"{tr['pnl']:+,.0f} $")
    print(f"{tr['strat'][:14]:14} {tr['entree']:%d/%m %H:%M} {tr['sym']:7}{tr['tf']:>4} {tr['sens']} {tr['etiq']:8} @ {tr['px']:<10} "
          f"→ {tr['raison'] or '—':<16} {pnl:>10}   historique : {tr['historique']}")


def stats(sous, titre):
    fini = sous[sous["pnl"].notna()]
    if fini.empty:
        return
    g, p = fini.loc[fini["pnl"] > 0, "pnl"].sum(), -fini.loc[fini["pnl"] <= 0, "pnl"].sum()
    print(f"{titre:30} {len(sous):3} trades · {len(fini):3} terminés · {100 * (fini['pnl'] > 0).mean():5.1f} % gagnants · "
          f"PF {g / p if p else float('inf'):5.2f} · net {fini['pnl'].sum():+,.0f} $")


print("\nBILAN EN DIRECT")
for (st, sym, tf), s in df.groupby(["strat", "sym", "tf"]):
    stats(s, f"{st[:14]} {sym} {tf} tous")
    for etiq, s2 in s.groupby("etiq"):
        stats(s2, f"{st[:14]} {sym} {tf} {etiq}")
print("\nFANTÔMES (trades en direct comparés à l'historique)")
print(df.groupby(["strat", "etiq", "historique"]).size().to_string())
if verrou:
    # Listes à coller dans Strat5669verrou.pine (réglage « Trades vécus en direct »), une par stratégie / symbole.
    os.makedirs(verrou, exist_ok=True)
    for (st, sym, tf), s in df.groupby(["strat", "sym", "tf"]):
        ids = set(s["id"])
        t_ids = logs[logs["ID de l'alerte"].isin(ids)]["t"]
        lignes = [f"DEBUT {t_ids.min():%Y-%m-%d %H:%M}"]
        lignes += [f"{r.entree:%Y-%m-%d %H:%M} {r.sens} {'G' if r.etiq == 'GODLIKE' else '5'}" for r in s.sort_values("entree").itertuples()]
        lignes.append(f"FIN {t_ids.max():%Y-%m-%d %H:%M}")
        nom = os.path.join(verrou, f"verrou_{st}_{sym.replace('!', '')}_{tf}.txt")
        open(nom, "w", encoding="utf-8").write("\n".join(lignes) + "\n")
        print(f"Liste verrou : {nom} ({len(s)} trades)")
if suivi:
    # Fiche de suivi à remplir par Jeremy : une ligne par alerte d'entrée (ajoutée automatiquement), les colonnes
    # « Pris ? » à « Remarque » sont à lui et ne sont jamais écrasées.
    cle = ["Date", "Heure alerte", "Actif", "Sens"]
    perso = ["Pris ? (oui/non)", "Pourquoi pas pris", "Mon entrée", "Ma sortie", "Mon P&L $", "Remarque (fantôme vu, capture…)"]
    auto = pd.DataFrame({"Date": df["entree"].dt.strftime("%Y-%m-%d"), "Heure alerte": df["entree"].dt.strftime("%H:%M"),
                         "Actif": df["sym"], "Sens": df["sens"].map({"L": "long", "S": "short"}), "Étiquette": df["etiq"],
                         "Résultat alerte": df["raison"].fillna("en cours"),
                         "P&L alerte $ (2 micros)": df["pnl"].round(0), "Dans l'historique": df["historique"]})
    if os.path.exists(suivi):
        old = pd.read_csv(suivi, sep=";", dtype=str).fillna("")
        auto = auto.astype(str).replace("nan", "").merge(old[cle + [c for c in perso if c in old.columns]], on=cle, how="left")
    for c in perso:
        if c not in auto.columns:
            auto[c] = ""
    auto.astype(object).fillna("").sort_values(["Date", "Heure alerte"]).to_csv(suivi, sep=";", index=False)
    print(f"Fiche de suivi : {suivi} ({len(auto)} alertes)")
if sortie:
    df.to_csv(sortie, index=False)
    print(f"\nTable écrite dans {sortie}")
