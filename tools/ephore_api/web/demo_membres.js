export const VERSION_ETAT_DEMO = 1;

export const EQUITE_DEPART_DEFAUT = 1e4;

export const FRAIS_TAUX_DEFAUT = 45e-5;

export const NOTIONNEL_MINIMUM = 10;

export const LEVIER_DEFAUT = 1;

export const LEVIER_MAX = 50;

export const LIMITES_DEMO = [ "funding non simulé (la place le règle chaque heure)", "frais du palier de base de la place, sans remise de volume ni de parrainage", "carnet lu au meilleur prix seulement : un ordre se remplit en entier au premier prix, et un TP touché se remplit à l'instant", "TP, SL et liquidation déclenchés sur le prix reçu par le cockpit (en direct : médiane du bid, de l'ask et du dernier échange), pas sur le mark officiel de la place ; la liquidation démo garde aussi la maintenance du premier palier de marge de l’actif : au-delà de son premier seuil de palier, la place exige plus de marge de maintenance et liquide plus tôt", "liquidation toujours pour la position entière (la place n’en ferme que 20 % au-delà de 100 000 USDC) ; profondeur du carnet inconnue : une sortie sous les 2/3 de la maintenance est toujours traitée comme une reprise par le liquidateur de secours, qui garde toute la marge isolée, ou tout le compte croisé", "journal démo gardé dans ce navigateur, non déposé sur la plateforme", "page fermée ou en veille : aucun suivi ; au retour en démo directe, bougies complètes d'une minute disponibles rejouées sans carnet historique, lacunes possibles ; sorties au niveau sauf saut défavorable et borne de faillite", "résultats simulés, sans valeur prédictive" ];

export const LIMITES_DEMO_EN = [ "funding not simulated (the venue settles it every hour)", "fees of the venue's base tier, with no volume or referral discount", "book read at the best price only: an order fills entirely at the first price, and a touched TP fills at once", "TP, SL and liquidation triggered on the price the cockpit receives (live: median of bid, ask and last trade), not on the venue's official mark; the demo liquidation also keeps the maintenance of the asset's first margin tier: above the asset's first tier threshold, the venue requires more maintenance margin and liquidates sooner", "liquidation always for the whole position (the venue closes only 20% above 100,000 USDC); book depth unknown: an exit below 2/3 of maintenance is always treated as a backstop liquidator takeover, which keeps the whole isolated margin, or the whole cross account", "demo journal kept in this browser, not stored on the platform", "page closed or asleep: no monitoring; on return in live demo, available complete one-minute candles replayed without a historical book, gaps possible; exits at the level except adverse gaps and the bankruptcy cap", "simulated results, with no predictive value" ];

export const LIMITES_DEMO_GRATUIT = [ "données différées d'une heure", "TP et SL jugés sur des bougies de 2 min closes (un niveau peut être vu touché jusqu'à 3 minutes après le marché différé) ; après une absence, seules les bougies disponibles après le dernier jugement sont rejouées, sans reconstituer les lacunes" ];

export const LIMITES_DEMO_GRATUIT_EN = [ "data delayed by one hour", "TP and SL judged on closed 2-minute candles (a level can be seen as hit up to 3 minutes after the delayed market); after an absence, only available candles after the last judgment are replayed, without reconstructing gaps" ];

function _arrondirTaille(x) {
return Math.round(x * 1e10) / 1e10;
}

function _arrondirArgent(x) {
return Math.round(x * 1e8) / 1e8;
}

function _nombre(x) {
return typeof x === "number" && Number.isFinite(x);
}

function _coinSain(coin) {
return typeof coin === "string" && coin.length > 0 && coin.trim() === coin && !(coin in Object.prototype) && coin !== "prototype";
}

const _COTE_ACHAT = {
buy: 1,
long: 1,
achat: 1,
B: 1
};

const _COTE_VENTE = {
sell: 1,
short: 1,
vente: 1,
A: 1
};

function _lireCote(sens) {
if (typeof sens !== "string") return null;
if (_COTE_ACHAT[sens]) return "achat";
if (_COTE_VENTE[sens]) return "vente";
return null;
}

function _usd(x) {
return Number(x).toFixed(2) + " $";
}

function _lireFrais(frais) {
if (frais === undefined || frais === null) return {
frais: null
};
if (typeof frais !== "object") return {
refus: "frais illisibles : {preneur, apporteur, liquidation} attendus"
};
for (const k of [ "preneur", "apporteur", "liquidation" ]) {
if (!_nombre(frais[k]) || frais[k] < 0 || frais[k] >= .01) {
return {
refus: "frais illisibles : le taux « " + k + " » doit être entre 0 et 1 %"
};
}
}
return {
frais: {
preneur: frais.preneur,
apporteur: frais.apporteur,
liquidation: frais.liquidation
}
};
}

function _tauxFrais(etat, pos, role) {
const f = pos && pos.frais;
return f && _nombre(f[role]) ? f[role] : etat.frais_taux;
}

function _verifierEtat(etat) {
if (!etat || typeof etat !== "object" || etat.version !== VERSION_ETAT_DEMO || etat.mode !== "demo" || !etat.positions || !etat.marks || !Array.isArray(etat.remplissages) || !_nombre(etat.solde)) {
return {
refus: "état démo illisible : crée le compte avec creerCompteDemo ou restaure-le avec restaurer"
};
}
return null;
}

function _horodater(etat, t) {
if (t !== undefined && t !== null && !_nombre(t)) {
return {
refus: "instant illisible : t doit être un nombre de millisecondes"
};
}
let tt = _nombre(t) ? t : etat.t_courant_ms;
if (tt === null || tt === undefined) {
return {
refus: "aucun instant connu : passe t (millisecondes) ou envoie un prix d'abord"
};
}
if (_nombre(etat.t_courant_ms) && tt < etat.t_courant_ms) tt = etat.t_courant_ms;
etat.t_courant_ms = tt;
return {
t: tt
};
}

export function creerCompteDemo(options) {
const o = options || {};
const equite_depart = o.equite_depart === undefined ? EQUITE_DEPART_DEFAUT : o.equite_depart;
const frais_taux = o.frais_taux === undefined ? FRAIS_TAUX_DEFAUT : o.frais_taux;
if (!_nombre(equite_depart) || equite_depart <= 0) {
return {
refus: "équité de départ illisible : un nombre de dollars strictement positif est attendu"
};
}
if (!_nombre(frais_taux) || frais_taux < 0 || frais_taux >= .01) {
return {
refus: "taux de frais illisible : un taux entre 0 et 1 % est attendu (0,00045 = 0,045 %)"
};
}
let cree_le_ms = null;
if (typeof o.horloge === "function") cree_le_ms = o.horloge(); else if (o.horloge !== undefined && o.horloge !== null) cree_le_ms = o.horloge;
if (cree_le_ms !== null && !_nombre(cree_le_ms)) {
return {
refus: "horloge illisible : une fonction qui rend des millisecondes, ou un nombre, est attendue"
};
}
return {
version: VERSION_ETAT_DEMO,
mode: "demo",
equite_depart: equite_depart,
frais_taux: frais_taux,
cree_le_ms: cree_le_ms,
t_courant_ms: cree_le_ms,
solde: equite_depart,
frais_cumules: 0,
pnl_ferme_cumule: 0,
juge_ms: {},
marks: {},
positions: {},
leviers: {},
remplissages: [],
prochain_tid: 1,
prochain_oid: 1,
nb_reinitialisations: 0,
reinitialise_le_ms: null,
limites: LIMITES_DEMO.slice()
};
}

export function serialiser(etat) {
const e = _verifierEtat(etat);
if (e) return e;
return JSON.stringify(etat);
}

export function restaurer(source) {
let brut = source;
if (typeof source === "string") {
try {
brut = JSON.parse(source);
} catch (e) {
return {
refus: "état démo illisible : JSON invalide"
};
}
}
if (!brut || typeof brut !== "object") return {
refus: "état démo illisible : un objet est attendu"
};
if (brut.version !== VERSION_ETAT_DEMO) {
return {
refus: "état démo d'une autre version (" + String(brut.version) + ") : repars d'un compte neuf"
};
}
if (brut.mode !== "demo") return {
refus: "état démo illisible : le mode n'est pas « demo »"
};
if (!_nombre(brut.equite_depart) || brut.equite_depart <= 0) return {
refus: "état démo illisible : équité de départ"
};
if (!_nombre(brut.frais_taux) || brut.frais_taux < 0 || brut.frais_taux >= .01) return {
refus: "état démo illisible : taux de frais"
};
if (!_nombre(brut.solde)) return {
refus: "état démo illisible : solde"
};
if (!brut.marks || typeof brut.marks !== "object" || Array.isArray(brut.marks)) return {
refus: "état démo illisible : marks"
};
if (!brut.positions || typeof brut.positions !== "object" || Array.isArray(brut.positions)) return {
refus: "état démo illisible : positions"
};
if (!Array.isArray(brut.remplissages)) return {
refus: "état démo illisible : remplissages"
};
if (!Number.isInteger(brut.prochain_tid) || brut.prochain_tid < 1 || !Number.isInteger(brut.prochain_oid) || brut.prochain_oid < 1) {
return {
refus: "état démo illisible : compteurs d'identifiants"
};
}
for (const coin in brut.marks) {
const m = brut.marks[coin];
if (!_coinSain(coin) || !m || !_nombre(m.prix) || m.prix <= 0 || !_nombre(m.t)) {
return {
refus: "état démo illisible : mark de « " + coin + " »"
};
}
}
for (const coin in brut.positions) {
const p = brut.positions[coin];
if (!_coinSain(coin) || !p || p.coin !== coin || !_nombre(p.taille_signee) || p.taille_signee === 0 || !_nombre(p.prix_entree) || p.prix_entree <= 0 || !Number.isInteger(p.levier) || p.levier < 1 || p.levier > LEVIER_MAX || p.tp !== null && !_nombre(p.tp) || p.sl !== null && !_nombre(p.sl) || p.frais !== undefined && p.frais !== null && _lireFrais(p.frais).refus || p.levier_max !== undefined && p.levier_max !== null && (!Number.isInteger(p.levier_max) || p.levier_max < 1 || p.levier_max > LEVIER_MAX) || p.croise !== undefined && typeof p.croise !== "boolean" || !brut.marks[coin]) {
return {
refus: "état démo illisible : position sur « " + coin + " »"
};
}
}
for (let i = 0; i < brut.remplissages.length; i++) {
const f = brut.remplissages[i];
if (!f || !_coinSain(f.coin) || !_nombre(f.quand) || !_nombre(f.taille) || f.taille <= 0 || !_nombre(f.prix) || !_nombre(f.frais) || !_nombre(f.pnl) || !Number.isInteger(f.tid)) {
return {
refus: "état démo illisible : remplissage n°" + (i + 1)
};
}
}
const copie = JSON.parse(JSON.stringify(brut));
copie.leviers = copie.leviers && typeof copie.leviers === "object" ? copie.leviers : {};
copie.frais_cumules = _nombre(copie.frais_cumules) ? copie.frais_cumules : 0;
copie.pnl_ferme_cumule = _nombre(copie.pnl_ferme_cumule) ? copie.pnl_ferme_cumule : 0;
copie.nb_reinitialisations = Number.isInteger(copie.nb_reinitialisations) ? copie.nb_reinitialisations : 0;
if (copie.reinitialise_le_ms === undefined) copie.reinitialise_le_ms = null;
if (copie.cree_le_ms === undefined) copie.cree_le_ms = null;
if (copie.t_courant_ms === undefined || copie.t_courant_ms !== null && !_nombre(copie.t_courant_ms)) copie.t_courant_ms = null;
const jugements = copie.juge_ms;
copie.juge_ms = jugements && typeof jugements === "object" && !Array.isArray(jugements) && Object.keys(jugements).every(coin => _coinSain(coin) && _nombre(jugements[coin]) && jugements[coin] > 0) ? jugements : {};
copie.limites = LIMITES_DEMO.slice();
return copie;
}

export function migrerPositionsAvant(etat, regles) {
const e = _verifierEtat(etat);
if (e) return e;
const migrees = [];
if (!regles || typeof regles !== "object") return {
ok: true,
migrees: migrees
};
for (const coin of Object.keys(etat.positions)) {
const p = etat.positions[coin];
const r = Object.prototype.hasOwnProperty.call(regles, coin) ? regles[coin] : null;
const ancienne = p && !Number.isInteger(p.levier_max);
const corrigerMode = p && r && r.seulement_isole === true && p.croise !== false;
if (!p || !ancienne && !corrigerMode) continue;
if (!r || !Number.isInteger(r.levier_max) || r.levier_max < 1 || r.levier_max > LEVIER_MAX) continue;
if (r.seulement_isole !== undefined && typeof r.seulement_isole !== "boolean") continue;
const f = _lireFrais(r.frais);
if (f.refus) continue;
if (ancienne) {
p.levier_max = r.levier_max;
if (p.levier > r.levier_max) p.levier = r.levier_max;
if (f.frais) p.frais = f.frais;
}
if (r.seulement_isole === true) p.croise = false; else if (typeof p.croise !== "boolean") p.croise = true;
migrees.push(coin);
}
return {
ok: true,
migrees: migrees
};
}

function _latentPosition(etat, p) {
const m = etat.marks[p.coin];
if (!m) return 0;
return (m.prix - p.prix_entree) * p.taille_signee;
}

function _margePosition(p) {
return Math.abs(p.taille_signee) * p.prix_entree / p.levier;
}

function _prixLiquidation(etat, p) {
return _prixSeuilMaintenance(etat, p, 1);
}

function _prixSecours(etat, p) {
return _prixSeuilMaintenance(etat, p, 2 / 3);
}

function _prixSeuilMaintenance(etat, p, k) {
if (!Number.isInteger(p.levier_max) || p.levier_max < 1) return null;
const l = k / (2 * p.levier_max);
const T = Math.abs(p.taille_signee);
if (!(T > 0)) return null;
let X;
if (p.croise !== false) {
X = etat.solde;
for (const c in etat.positions) {
if (c === p.coin) continue;
const q = etat.positions[c];
if (q.croise === false) {
X -= _margePosition(q);
continue;
}
X += _latentPosition(etat, q);
const mq = etat.marks[c];
if (mq && Number.isInteger(q.levier_max) && q.levier_max >= 1) X -= k * Math.abs(q.taille_signee) * mq.prix / (2 * q.levier_max);
}
} else {
X = _margePosition(p);
}
const liq = p.taille_signee > 0 ? (p.prix_entree * T - X) / (T * (1 - l)) : (p.prix_entree * T + X) / (T * (1 + l));
return _nombre(liq) && liq > 0 ? Math.round(liq * 1e6) / 1e6 : null;
}

export function margeCroiseeDisponible(etat, coin) {
if (_verifierEtat(etat) || !_coinSain(coin)) return {
repli: "marge_illisible"
};
if (etat.positions[coin]) return {
repli: "position_ouverte"
};
let X = etat.solde;
for (const c in etat.positions) {
const q = etat.positions[c];
if (q.croise === false) {
X -= _margePosition(q);
continue;
}
const mq = etat.marks[c];
if (!mq || mq.indicatif === true || !Number.isInteger(q.levier_max) || q.levier_max < 1) return {
repli: "voisin_sans_prix"
};
X += _latentPosition(etat, q);
X -= Math.abs(q.taille_signee) * mq.prix / (2 * q.levier_max);
}
return Number.isFinite(X) ? {
valeur: X
} : {
repli: "marge_illisible"
};
}

function _voisinCroiseIndicatif(etat, p) {
if (p.croise === false) return false;
for (const c in etat.positions) {
if (c === p.coin) continue;
const q = etat.positions[c];
if (q.croise === false) continue;
const mq = etat.marks[c];
if (!mq || mq.indicatif === true) return true;
}
return false;
}

function _margePortante(etat, p) {
let X;
if (p.croise !== false) {
X = etat.solde;
for (const c in etat.positions) {
if (c === p.coin) continue;
const q = etat.positions[c];
if (q.croise === false) X -= _margePosition(q); else X += _latentPosition(etat, q);
}
} else {
X = _margePosition(p);
}
return X;
}

function _prixFaillite(etat, p) {
const T = Math.abs(p.taille_signee);
if (!(T > 0)) return null;
const X = _margePortante(etat, p);
const bk = p.taille_signee > 0 ? p.prix_entree - X / T : p.prix_entree + X / T;
return _nombre(bk) && bk > 0 ? bk : null;
}

function _prixPlaceDefavorable(x, vente) {
if (!_nombre(x) || x <= 0) return x;
const pas = 10 ** (Math.floor(Math.log10(x)) - 4);
const v = vente ? Math.floor(x / pas + 1e-9) * pas : Math.ceil(x / pas - 1e-9) * pas;
return Number(v.toPrecision(5));
}

export function pnlLatent(etat, coin) {
if (_verifierEtat(etat)) return 0;
let total = 0;
for (const c in etat.positions) {
if (coin !== undefined && coin !== null && c !== coin) continue;
total += _latentPosition(etat, etat.positions[c]);
}
return total;
}

export function margeUtilisee(etat) {
if (_verifierEtat(etat)) return 0;
let total = 0;
for (const c in etat.positions) total += _margePosition(etat.positions[c]);
return total;
}

export function equite(etat) {
if (_verifierEtat(etat)) return null;
return etat.solde + pnlLatent(etat);
}

export function resume(etat) {
const e = _verifierEtat(etat);
if (e) return e;
const latent = pnlLatent(etat);
const marge = margeUtilisee(etat);
const eq = etat.solde + latent;
return {
ok: true,
mode: "demo",
simule: true,
equite_depart: etat.equite_depart,
frais_taux: etat.frais_taux,
solde: etat.solde,
pnl_latent: latent,
equite: eq,
marge_utilisee: marge,
disponible: eq - marge,
frais_cumules: etat.frais_cumules,
pnl_ferme_cumule: etat.pnl_ferme_cumule,
nb_positions: Object.keys(etat.positions).length,
nb_remplissages: etat.remplissages.length,
t_courant_ms: etat.t_courant_ms,
limites: etat.limites.slice()
};
}

export function pnlDepuis(etat, debut_ms) {
const e = _verifierEtat(etat);
if (e) return e;
if (!_nombre(debut_ms)) return {
refus: "instant illisible : debut_ms doit être un nombre de millisecondes"
};
let realise = 0, nb = 0;
for (const f of etat.remplissages) {
if (f.quand < debut_ms) continue;
realise += f.pnl - f.frais;
nb += 1;
}
realise = _arrondirArgent(realise);
const latent = pnlLatent(etat);
return {
ok: true,
depuis_ms: debut_ms,
realise: realise,
latent: latent,
total: _arrondirArgent(realise + latent),
nb_remplissages: nb
};
}

function _fabriquerRemplissage(etat, p) {
const frais = _arrondirArgent(p.taille * p.prix * (_nombre(p.frais_taux) ? p.frais_taux : etat.frais_taux));
const pnl = _arrondirArgent(p.pnl || 0);
const tid = etat.prochain_tid;
etat.prochain_tid += 1;
etat.solde = _arrondirArgent(etat.solde + pnl - frais);
etat.frais_cumules = _arrondirArgent(etat.frais_cumules + frais);
etat.pnl_ferme_cumule = _arrondirArgent(etat.pnl_ferme_cumule + pnl);
const f = {
tid: tid,
oid: p.oid,
quand: p.t,
coin: p.coin,
sens: p.dir,
taille: p.taille,
prix: p.prix,
frais: frais,
jeton_frais: "USDC",
pnl: pnl,
croisement: p.apporteur ? "apporteur" : "preneur",
cote: p.cote,
position_avant: p.position_avant,
time: p.t,
dir: p.dir,
side: p.cote === "achat" ? "B" : "A",
sz: p.taille,
px: p.prix,
fee: frais,
feeToken: "USDC",
closedPnl: pnl,
crossed: !p.apporteur,
startPosition: p.position_avant,
horodatage_ms: p.t,
origine: "demo",
motif_demo: p.motif,
marche_ms: _nombre(p.marche_ms) && p.marche_ms > 0 ? p.marche_ms : null
};
if (p.secours === true) f.secours = true;
etat.remplissages.push(f);
return f;
}

function _remplir(etat, p) {
const pos = etat.positions[p.coin] || null;
const avant = pos ? pos.taille_signee : 0;
const delta = p.cote === "achat" ? p.taille : -p.taille;
const fills = [];
const mk = etat.marks[p.coin];
const commun = {
coin: p.coin,
cote: p.cote,
prix: p.prix,
t: p.t,
oid: p.oid,
motif: p.motif,
frais_taux: p.frais_taux,
apporteur: !!p.apporteur,
secours: p.secours === true,
marche_ms: mk && _nombre(mk.marche_t) && mk.marche_t > 0 ? mk.marche_t : null
};
if (avant === 0 || avant > 0 === delta > 0) {
const apres = _arrondirTaille(avant + delta);
fills.push(_fabriquerRemplissage(etat, Object.assign({}, commun, {
taille: p.taille,
dir: delta > 0 ? "Open Long" : "Open Short",
pnl: 0,
position_avant: avant
})));
if (pos) {
pos.prix_entree = _arrondirArgent((Math.abs(avant) * pos.prix_entree + p.taille * p.prix) / Math.abs(apres));
pos.taille_signee = apres;
if (p.levier) pos.levier = p.levier;
} else {
etat.positions[p.coin] = _positionNeuve(p.coin, apres, p.prix, p.levier, p.t);
}
return fills;
}
const signe = avant > 0 ? 1 : -1;
const aFermer = Math.min(p.taille, Math.abs(avant));
const prixEntree = pos.prix_entree;
fills.push(_fabriquerRemplissage(etat, Object.assign({}, commun, {
taille: aFermer,
dir: signe > 0 ? "Close Long" : "Close Short",
pnl: (p.prix - prixEntree) * aFermer * signe,
position_avant: avant
})));
const reste = _arrondirTaille(Math.abs(avant) - aFermer);
if (reste === 0) delete etat.positions[p.coin]; else pos.taille_signee = signe * reste;
const surplus = _arrondirTaille(p.taille - aFermer);
if (surplus > 0) {
fills.push(_fabriquerRemplissage(etat, Object.assign({}, commun, {
taille: surplus,
dir: delta > 0 ? "Open Long" : "Open Short",
pnl: 0,
position_avant: 0
})));
etat.positions[p.coin] = _positionNeuve(p.coin, delta > 0 ? surplus : -surplus, p.prix, p.levier || pos.levier, p.t);
}
return fills;
}

function _positionNeuve(coin, taille_signee, prix_entree, levier, t) {
return {
coin: coin,
taille_signee: taille_signee,
prix_entree: prix_entree,
levier: levier || LEVIER_DEFAUT,
tp: null,
sl: null,
tp_oid: null,
sl_oid: null,
tp_pose_ms: null,
sl_pose_ms: null,
ouverte_le_ms: t
};
}

export function recevoirPrix(etat, coin, prix, t, marcheMs, carnet) {
const e = _verifierEtat(etat);
if (e) return e;
if (!_coinSain(coin)) return {
refus: "coin vide ou mal formé : un nom d'actif est attendu"
};
let bas, haut, cloture, ouverture = null;
if (_nombre(prix)) {
bas = haut = cloture = prix;
} else if (prix && typeof prix === "object") {
bas = prix.bas;
haut = prix.haut;
cloture = prix.cloture;
ouverture = prix.ouverture == null ? null : prix.ouverture;
if (!_nombre(bas) || !_nombre(haut) || !_nombre(cloture) || bas > haut || cloture < bas || cloture > haut || ouverture !== null && (!_nombre(ouverture) || ouverture < bas || ouverture > haut)) {
return {
refus: "bougie illisible : {bas, haut, cloture} numériques avec bas <= cloture <= haut et ouverture facultative dans ces bornes attendus"
};
}
} else return {
refus: "prix illisible : un nombre ou une bougie {bas, haut, cloture} est attendu"
};
if (bas <= 0) return {
refus: "prix illisible : un prix strictement positif est attendu"
};
if (!_nombre(t)) return {
refus: "instant illisible : t doit être un nombre de millisecondes"
};
const h = _horodater(etat, t);
if (h.refus) return h;
if (!etat.juge_ms || typeof etat.juge_ms !== "object" || Array.isArray(etat.juge_ms)) etat.juge_ms = {};
etat.juge_ms[coin] = h.t;
etat.marks[coin] = {
prix: cloture,
bas: bas,
haut: haut,
t: h.t,
marche_t: _nombre(marcheMs) && marcheMs > 0 ? marcheMs : null
};
const declenchements = [];
const pos = etat.positions[coin];
if (pos) {
const long = pos.taille_signee > 0;
const voisinIndicatif = _voisinCroiseIndicatif(etat, pos);
const liq = voisinIndicatif ? null : _prixLiquidation(etat, pos);
const slTouche = pos.sl !== null && (long ? bas <= pos.sl : haut >= pos.sl);
const tpTouche = pos.tp !== null && (long ? haut >= pos.tp : bas <= pos.tp);
const liqTouchee = liq !== null && (long ? bas <= liq : haut >= liq);
let role = null;
if (slTouche && !(liqTouchee && (long ? pos.sl <= liq : pos.sl >= liq))) role = "sl"; else if (liqTouchee) role = "liquidation"; else if (tpTouche) role = "tp";
if (role) {
const carnetSain = !!carnet && _nombre(carnet.bid) && _nombre(carnet.ask) && carnet.bid > 0 && carnet.ask >= carnet.bid;
const auCarnet = carnetSain ? long ? carnet.bid : carnet.ask : null;
const faillite = voisinIndicatif ? null : _prixFaillite(etat, pos);
const prixStop = auCarnet !== null ? auCarnet : ouverture !== null && (long ? ouverture < pos.sl : ouverture > pos.sl) ? ouverture : pos.sl;
const stopAuDelaFaillite = role === "sl" && faillite !== null && (long ? prixStop <= faillite : prixStop >= faillite);
if (stopAuDelaFaillite) role = "liquidation";
let prixSortie, taux, apporteur = false, oidSortie, reprise = false;
if (role === "sl") {
prixSortie = prixStop;
taux = _tauxFrais(etat, pos, "preneur");
oidSortie = pos.sl_oid;
} else if (role === "liquidation") {
prixSortie = auCarnet !== null ? auCarnet : stopAuDelaFaillite ? prixStop : ouverture !== null && (long ? ouverture <= liq : ouverture >= liq) ? ouverture : _prixPlaceDefavorable((long ? haut < liq : bas > liq) ? cloture : liq, long);
taux = _tauxFrais(etat, pos, "liquidation");
const secours = voisinIndicatif ? null : _prixSecours(etat, pos);
reprise = secours !== null && (long ? prixSortie <= secours : prixSortie >= secours) || faillite !== null && (long ? prixSortie * (1 - taux) <= faillite : prixSortie * (1 + taux) >= faillite);
if (reprise && faillite !== null) {
prixSortie = faillite;
taux = 0;
} else if (reprise) {
const reste = _margePortante(etat, pos) + (prixSortie - pos.prix_entree) * pos.taille_signee;
taux = reste > 0 ? reste / (Math.abs(pos.taille_signee) * prixSortie) : 0;
}
oidSortie = etat.prochain_oid;
etat.prochain_oid += 1;
} else {
oidSortie = pos.tp_oid;
if (auCarnet !== null && (long ? auCarnet >= pos.tp : auCarnet <= pos.tp)) {
prixSortie = auCarnet;
taux = _tauxFrais(etat, pos, "preneur");
} else if (auCarnet !== null) {
prixSortie = pos.tp;
taux = _tauxFrais(etat, pos, "apporteur");
apporteur = true;
} else {
prixSortie = pos.tp;
taux = _tauxFrais(etat, pos, "preneur");
}
}
if ((role === "sl" || role === "liquidation") && !voisinIndicatif) {
const T = Math.abs(pos.taille_signee);
const reste = _margePortante(etat, pos) + (prixSortie - pos.prix_entree) * pos.taille_signee;
if (T * prixSortie * taux > reste) taux = Math.max(0, reste) / (T * prixSortie);
}
const fills = _remplir(etat, {
coin: coin,
cote: long ? "vente" : "achat",
taille: Math.abs(pos.taille_signee),
prix: prixSortie,
t: h.t,
oid: oidSortie,
motif: role,
frais_taux: taux,
apporteur: apporteur,
secours: reprise
});
for (const f of fills) declenchements.push(f);
if (reprise && pos.croise !== false) {
for (const c of Object.keys(etat.positions).sort()) {
const q = etat.positions[c];
const mq = etat.marks[c];
if (!q || q.croise === false || !mq) continue;
const oidReprise = etat.prochain_oid;
etat.prochain_oid += 1;
const fq = _remplir(etat, {
coin: c,
cote: q.taille_signee > 0 ? "vente" : "achat",
taille: Math.abs(q.taille_signee),
prix: mq.prix,
t: h.t,
oid: oidReprise,
motif: "liquidation",
frais_taux: 0,
apporteur: false,
secours: true
});
for (const f of fq) declenchements.push(f);
}
}
}
}
return {
ok: true,
coin: coin,
mark: cloture,
declenchements: declenchements,
equite: equite(etat)
};
}

export function dernierJugement(etat, coin) {
if (!etat || !_coinSain(coin) || !etat.juge_ms || !Object.prototype.hasOwnProperty.call(etat.juge_ms, coin)) return null;
const t = etat.juge_ms[coin];
return _nombre(t) && t > 0 ? t : null;
}

export function marquerPrix(etat, coin, prix, t) {
const e = _verifierEtat(etat);
if (e) return e;
if (!_coinSain(coin)) return {
refus: "coin vide ou mal formé : un nom d'actif est attendu"
};
if (!_nombre(prix) || prix <= 0) return {
refus: "prix illisible : un prix strictement positif est attendu"
};
if (!_nombre(t)) return {
refus: "instant illisible : t doit être un nombre de millisecondes"
};
const h = _horodater(etat, t);
if (h.refus) return h;
etat.marks[coin] = {
prix: prix,
bas: prix,
haut: prix,
t: h.t,
marche_t: null,
indicatif: true
};
return {
ok: true,
coin: coin,
mark: prix,
declenchements: [],
equite: equite(etat)
};
}

function _lireLevier(levier) {
if (!Number.isInteger(levier) || levier < 1 || levier > LEVIER_MAX) {
return {
refus: "levier illisible : un entier entre 1 et " + LEVIER_MAX + " est attendu (la place plafonne par actif)"
};
}
return {
levier: levier
};
}

function _lirePaliersMarge(p) {
if (!Array.isArray(p) || p.length < 1 || p.length > 10) return null;
let prec = null;
for (const x of p) {
if (!x || !_nombre(x.borne) || x.borne < 0 || !Number.isInteger(x.levier_max) || x.levier_max < 1 || x.levier_max > LEVIER_MAX) return null;
if (prec && (x.borne <= prec.borne || x.levier_max > prec.levier_max)) return null;
prec = x;
}
return p[0].borne === 0 ? p : null;
}

function _verifierNiveaux(long, tp, sl, reference, motRef) {
if (tp !== null) {
if (!_nombre(tp) || tp <= 0) return {
refus: "TP illisible : un prix strictement positif est attendu"
};
if (long ? tp <= reference : tp >= reference) {
return {
refus: "TP du mauvais côté du prix (" + (long ? "au-dessus" : "en dessous") + " de " + motRef + " " + reference + " attendu pour un " + (long ? "long" : "short") + ") : il se déclencherait à l'instant"
};
}
}
if (sl !== null) {
if (!_nombre(sl) || sl <= 0) return {
refus: "SL illisible : un prix strictement positif est attendu"
};
if (long ? sl >= reference : sl <= reference) {
return {
refus: "SL du mauvais côté du prix (" + (long ? "en dessous" : "au-dessus") + " de " + motRef + " " + reference + " attendu pour un " + (long ? "long" : "short") + ") : il se déclencherait à l'instant"
};
}
}
return null;
}

export function entrer(etat, ordre, t) {
const e = _verifierEtat(etat);
if (e) return e;
if (!ordre || typeof ordre !== "object") return {
refus: "ordre illisible : un objet {coin, sens, taille, ...} est attendu"
};
const coin = ordre.coin;
if (!_coinSain(coin)) return {
refus: "coin vide ou mal formé : un nom d'actif est attendu"
};
const cote = _lireCote(ordre.sens);
if (!cote) return {
refus: 'sens illisible : "long" ou "short" (le vocabulaire de la page), "buy" ou "sell" attendus'
};
const mark = etat.marks[coin];
if (!mark) return {
refus: "aucun prix connu pour " + coin + " : le simulateur remplit au dernier prix du flux, attends le premier tick"
};
let prixExec = mark.prix;
if (ordre.prix_remplissage !== undefined && ordre.prix_remplissage !== null) {
if (!_nombre(ordre.prix_remplissage) || ordre.prix_remplissage <= 0) {
return {
refus: "prix de remplissage illisible : un prix strictement positif est attendu"
};
}
prixExec = ordre.prix_remplissage;
} else if (ordre.prix !== undefined && ordre.prix !== null) {
if (!_nombre(ordre.prix) || ordre.prix <= 0) return {
refus: "prix limite illisible : un prix strictement positif est attendu"
};
const atteignable = cote === "achat" ? ordre.prix >= mark.prix : ordre.prix <= mark.prix;
if (!atteignable) {
return {
refus: "prix limite " + ordre.prix + " non atteignable au mark " + mark.prix + " : le simulateur ne garde aucun ordre en attente, entre au marché ou rapproche ton prix"
};
}
prixExec = ordre.prix;
}
let taille;
if (ordre.taille !== undefined && ordre.taille !== null) {
if (!_nombre(ordre.taille) || ordre.taille <= 0) return {
refus: "taille illisible ou nulle : un nombre d'unités strictement positif est attendu"
};
taille = _arrondirTaille(ordre.taille);
} else if (ordre.montant !== undefined && ordre.montant !== null) {
if (!_nombre(ordre.montant) || ordre.montant <= 0) return {
refus: "montant illisible : un notionnel en dollars strictement positif est attendu"
};
taille = _arrondirTaille(ordre.montant / prixExec);
} else return {
refus: "taille absente : donne une taille en unités ou un montant en dollars"
};
if (!(taille > 0)) return {
refus: "taille nulle une fois arrondie : augmente la taille ou le montant"
};
const notionnel = taille * prixExec;
const planReel = ordre.prix_remplissage !== undefined && ordre.prix_remplissage !== null;
if (notionnel < NOTIONNEL_MINIMUM && !planReel) {
return {
refus: "notionnel de " + notionnel.toFixed(2) + " $ sous le plancher de " + NOTIONNEL_MINIMUM + " $ de la place (« Order must have minimum value of $10. »), règle gardée en démo"
};
}
const pos = etat.positions[coin] || null;
let levier = pos ? pos.levier : etat.leviers[coin] || LEVIER_DEFAUT;
if (ordre.levier !== undefined && ordre.levier !== null) {
const l = _lireLevier(ordre.levier);
if (l.refus) return l;
levier = l.levier;
}
const lusFrais = _lireFrais(ordre.frais);
if (lusFrais.refus) return lusFrais;
let levierMax = null;
if (ordre.levier_max !== undefined && ordre.levier_max !== null) {
if (!Number.isInteger(ordre.levier_max) || ordre.levier_max < 1 || ordre.levier_max > LEVIER_MAX) {
return {
refus: "plafond de levier de l'actif illisible : un entier entre 1 et " + LEVIER_MAX + " est attendu"
};
}
levierMax = ordre.levier_max;
if (levier > levierMax) {
return {
refus: "levier x" + levier + " au-dessus du plafond de " + coin + " (x" + levierMax + ") : la place le refuse"
};
}
}
if (ordre.croise !== undefined && ordre.croise !== null && typeof ordre.croise !== "boolean") {
return {
refus: "mode de marge illisible : croise vrai (croisée) ou faux (isolée) attendu"
};
}
let paliers = null;
if (ordre.paliers_marge !== undefined && ordre.paliers_marge !== null) {
paliers = _lirePaliersMarge(ordre.paliers_marge);
if (!paliers) return {
refus: "paliers de marge de l'actif illisibles : aucune entrée n'est simulée sur une règle illisible"
};
}
const tauxEntree = lusFrais.frais ? lusFrais.frais.preneur : _tauxFrais(etat, pos, "preneur");
const avant = pos ? pos.taille_signee : 0;
const delta = cote === "achat" ? taille : -taille;
const apres = _arrondirTaille(avant + delta);
const tp = ordre.tp === undefined || ordre.tp === null ? null : ordre.tp;
const sl = ordre.sl === undefined || ordre.sl === null ? null : ordre.sl;
if ((tp !== null || sl !== null) && apres === 0) {
return {
refus: "la position serait à plat après cet ordre : rien à protéger, retire le TP et le SL"
};
}
if (tp !== null || sl !== null) {
const v = _verifierNiveaux(apres > 0, tp, sl, prixExec, "prix d'exécution");
if (v) return v;
if (prixExec !== mark.prix && (ordre.prix_remplissage === undefined || ordre.prix_remplissage === null)) {
const vm = _verifierNiveaux(apres > 0, tp, sl, mark.prix, "mark");
if (vm) return vm;
}
}
if (Math.abs(apres) > Math.abs(avant)) {
if (paliers) {
const notionnelApres = Math.abs(apres) * prixExec;
for (let i = 0; i < paliers.length; i++) {
if (paliers[i].levier_max >= levier) continue;
if (notionnelApres > paliers[i].borne) {
return {
refus: "position de " + _usd(notionnelApres) + " de notionnel sur " + coin + " : au-delà de " + _usd(paliers[i].borne) + ", la place plafonne le levier à x" + paliers[i].levier_max + " et refuse x" + levier + " (« Order would cause position to exceed margin tier limit at current leverage ») : baisse le levier ou la taille",
code: "palier_marge",
notionnel: notionnelApres,
plafond: paliers[i].borne,
levier_palier: paliers[i].levier_max,
levier: levier
};
}
break;
}
}
const memeSens = avant === 0 || avant > 0 === delta > 0;
const peApres = memeSens ? (Math.abs(avant) * (pos ? pos.prix_entree : 0) + taille * prixExec) / Math.abs(apres) : prixExec;
const aFermer = memeSens ? 0 : Math.abs(avant);
const pnlGeste = memeSens ? 0 : (prixExec - pos.prix_entree) * aFermer * (avant > 0 ? 1 : -1);
const fraisGeste = taille * prixExec * tauxEntree;
const latentAvantCoin = pos ? _latentPosition(etat, pos) : 0;
const latentApresCoin = (mark.prix - peApres) * apres;
const equiteAvant = equite(etat);
const equiteApres = equiteAvant - latentAvantCoin + pnlGeste - fraisGeste + latentApresCoin;
const margeAutres = margeUtilisee(etat) - (pos ? _margePosition(pos) : 0);
const margeCoinApres = Math.abs(apres) * peApres / levier;
const disponibleApres = equiteApres - margeAutres - margeCoinApres;
if (disponibleApres < -1e-9) {
return {
refus: "marge insuffisante : " + _usd(margeCoinApres) + " de marge requis à x" + levier + " pour " + Math.abs(apres) + " " + coin + ", " + _usd(equiteAvant - margeUtilisee(etat)) + " disponibles (équité démo " + _usd(equiteAvant) + ") : réduis la taille ou monte le levier"
};
}
}
const h = _horodater(etat, t);
if (h.refus) return h;
const oid = etat.prochain_oid;
etat.prochain_oid += 1;
const fills = _remplir(etat, {
coin: coin,
cote: cote,
taille: taille,
prix: prixExec,
t: h.t,
oid: oid,
motif: "entree",
levier: levier,
frais_taux: tauxEntree
});
etat.leviers[coin] = levier;
const posApres = etat.positions[coin] || null;
if (posApres) {
posApres.levier = levier;
if (lusFrais.frais) posApres.frais = lusFrais.frais;
const neuve = !pos || posApres !== pos;
if (levierMax !== null && (neuve || !Number.isInteger(posApres.levier_max))) posApres.levier_max = levierMax;
if (typeof ordre.croise === "boolean" && (neuve || typeof posApres.croise !== "boolean")) posApres.croise = neuve ? ordre.croise : true;
if (tp !== null) {
posApres.tp = tp;
posApres.tp_oid = etat.prochain_oid;
etat.prochain_oid += 1;
posApres.tp_pose_ms = h.t;
}
if (sl !== null) {
posApres.sl = sl;
posApres.sl_oid = etat.prochain_oid;
etat.prochain_oid += 1;
posApres.sl_pose_ms = h.t;
}
}
return {
ok: true,
coin: coin,
oid: oid,
prix: prixExec,
taille: taille,
remplissages: fills,
position: posApres ? _positionInterne(etat, posApres) : null,
equite: equite(etat)
};
}

export function fermer(etat, coin, taille, t, prix) {
const e = _verifierEtat(etat);
if (e) return e;
if (prix !== undefined && prix !== null && (!_nombre(prix) || prix <= 0)) {
return {
refus: "prix de fermeture illisible : un prix strictement positif est attendu"
};
}
if (!_coinSain(coin)) return {
refus: "coin vide ou mal formé : un nom d'actif est attendu"
};
const pos = etat.positions[coin];
if (!pos) return {
refus: "aucune position démo sur " + coin + " : rien à fermer",
rien_a_fermer: true
};
let aFermer = Math.abs(pos.taille_signee);
let ramenee = false;
if (taille !== undefined && taille !== null) {
if (!_nombre(taille) || taille <= 0) return {
refus: "taille illisible ou nulle : un nombre d'unités strictement positif est attendu"
};
if (taille < aFermer) aFermer = _arrondirTaille(taille); else if (taille > aFermer) ramenee = true;
}
const mark = etat.marks[coin];
if (!mark) return {
refus: "aucun prix connu pour " + coin + " : impossible de fermer sans mark"
};
const h = _horodater(etat, t);
if (h.refus) return h;
const oid = etat.prochain_oid;
etat.prochain_oid += 1;
const prixFermeture = _nombre(prix) ? prix : mark.prix;
const fills = _remplir(etat, {
coin: coin,
cote: pos.taille_signee > 0 ? "vente" : "achat",
taille: aFermer,
prix: prixFermeture,
t: h.t,
oid: oid,
motif: "manuel",
frais_taux: _tauxFrais(etat, pos, "preneur")
});
const reste = etat.positions[coin] || null;
return {
ok: true,
coin: coin,
oid: oid,
prix: prixFermeture,
taille: aFermer,
taille_ramenee_a_la_position: ramenee,
remplissages: fills,
position: reste ? _positionInterne(etat, reste) : null,
equite: equite(etat)
};
}

export function reduire(etat, coin, taille, t) {
if (!_nombre(taille) || taille <= 0) return {
refus: "taille illisible ou nulle : réduire exige un nombre d'unités strictement positif"
};
return fermer(etat, coin, taille, t);
}

export function flatten(etat, t) {
const e = _verifierEtat(etat);
if (e) return e;
const coins = Object.keys(etat.positions).sort();
if (!coins.length) return {
refus: "aucune position démo ouverte : rien à fermer",
rien_a_fermer: true
};
const fills = [];
for (const coin of coins) {
const r = fermer(etat, coin, undefined, t);
if (r.refus) return r;
for (const f of r.remplissages) fills.push(f);
}
return {
ok: true,
nb_fermees: coins.length,
coins: coins,
remplissages: fills,
equite: equite(etat)
};
}

export function poserTpsl(etat, coin, tp, sl) {
const e = _verifierEtat(etat);
if (e) return e;
if (!_coinSain(coin)) return {
refus: "coin vide ou mal formé : un nom d'actif est attendu"
};
const pos = etat.positions[coin];
if (!pos) return {
refus: "aucune position démo sur " + coin + " : rien à protéger",
rien_a_proteger: true
};
const mark = etat.marks[coin];
const tpN = tp === undefined ? pos.tp : tp === null ? null : tp;
const slN = sl === undefined ? pos.sl : sl === null ? null : sl;
const v = _verifierNiveaux(pos.taille_signee > 0, tpN, slN, mark.prix, "mark");
if (v) return v;
if (tp !== undefined) {
pos.tp = tpN;
pos.tp_oid = tpN === null ? null : etat.prochain_oid;
if (tpN !== null) etat.prochain_oid += 1;
pos.tp_pose_ms = tpN === null ? null : etat.t_courant_ms;
}
if (sl !== undefined) {
pos.sl = slN;
pos.sl_oid = slN === null ? null : etat.prochain_oid;
if (slN !== null) etat.prochain_oid += 1;
pos.sl_pose_ms = slN === null ? null : etat.t_courant_ms;
}
return {
ok: true,
coin: coin,
tp: pos.tp,
sl: pos.sl,
tp_oid: pos.tp_oid,
sl_oid: pos.sl_oid
};
}

export function annuler(etat, coin, quoi) {
const e = _verifierEtat(etat);
if (e) return e;
if (!_coinSain(coin)) return {
refus: "coin vide ou mal formé : un nom d'actif est attendu"
};
const pos = etat.positions[coin];
if (!pos) return {
refus: "aucune position démo sur " + coin + " : rien à annuler",
rien_a_annuler: true
};
if (quoi !== undefined && quoi !== null && quoi !== "tp" && quoi !== "sl" && quoi !== "tpsl") {
return {
refus: 'cible illisible : "tp", "sl" ou rien (les deux) attendus'
};
}
const tousDeux = quoi === undefined || quoi === null || quoi === "tpsl";
if (tousDeux || quoi === "tp") {
pos.tp = null;
pos.tp_oid = null;
pos.tp_pose_ms = null;
}
if (tousDeux || quoi === "sl") {
pos.sl = null;
pos.sl_oid = null;
pos.sl_pose_ms = null;
}
return {
ok: true,
coin: coin,
tp: pos.tp,
sl: pos.sl
};
}

export function breakEvenAuto(etat, coin, options) {
const e = _verifierEtat(etat);
if (e) return e;
if (!_coinSain(coin)) return {
refus: "coin vide ou mal formé : un nom d'actif est attendu"
};
const o = options || {};
if (!_nombre(o.seuil_r) || o.seuil_r <= 0) {
return {
refus: "seuil du break-even automatique illisible : un nombre de R strictement positif est attendu"
};
}
if (!_nombre(o.marge) || o.marge < 0) {
return {
refus: "marge du break-even automatique illisible : une marge en prix, positive ou nulle, est attendue (marge_break_even)"
};
}
if (o.prix_sortie !== undefined && o.prix_sortie !== null && (!_nombre(o.prix_sortie) || o.prix_sortie <= 0)) {
return {
refus: "prix de sortie illisible : un prix strictement positif est attendu"
};
}
const pos = etat.positions[coin];
if (!pos) return {
ok: true,
coin: coin,
pose: false,
motif: "aucune position"
};
if (pos.sl === null) return {
ok: true,
coin: coin,
pose: false,
motif: "aucun stop sur la position"
};
const mark = etat.marks[coin];
if (!mark) return {
ok: true,
coin: coin,
pose: false,
motif: "aucun mark connu"
};
const long = pos.taille_signee > 0;
const pe = pos.prix_entree;
if (pos.be_fait_pe === pe) return {
ok: true,
coin: coin,
pose: false,
motif: "déjà posé sur cette position (cliquet)"
};
const dejaBon = long ? pos.sl >= pe : pos.sl <= pe;
if (dejaBon) {
pos.be_fait_pe = pe;
return {
ok: true,
coin: coin,
pose: false,
motif: "stop déjà au point mort ou au-delà (cliquet armé)"
};
}
const distance = Math.abs(pe - pos.sl);
if (!(distance > 0)) return {
ok: true,
coin: coin,
pose: false,
motif: "distance au stop nulle"
};
const prix = _nombre(o.prix_sortie) ? o.prix_sortie : mark.prix;
const avance = long ? prix - pe : pe - prix;
if (!(avance > Math.max(o.seuil_r * distance, o.marge))) {
return {
ok: true,
coin: coin,
pose: false,
motif: "seuil non atteint",
avance: avance,
distance: distance,
seuil_prix: Math.max(o.seuil_r * distance, o.marge)
};
}
const cible = Math.round((long ? pe + o.marge : pe - o.marge) * 1e6) / 1e6;
if (_verifierNiveaux(long, null, cible, mark.prix, "mark")) {
return {
ok: true,
coin: coin,
pose: false,
motif: "cible du mauvais côté du mark",
cible: cible
};
}
const slAvant = pos.sl;
pos.sl = cible;
pos.sl_oid = etat.prochain_oid;
etat.prochain_oid += 1;
pos.sl_pose_ms = etat.t_courant_ms;
pos.be_fait_pe = pe;
return {
ok: true,
coin: coin,
pose: true,
sl: pos.sl,
sl_avant: slAvant,
sl_oid: pos.sl_oid,
prix_entree: pe,
marge: o.marge,
seuil_r: o.seuil_r,
avance: avance,
distance: distance
};
}

export function poserLevier(etat, coin, levier) {
const e = _verifierEtat(etat);
if (e) return e;
if (!_coinSain(coin)) return {
refus: "coin vide ou mal formé : un nom d'actif est attendu"
};
const l = _lireLevier(levier);
if (l.refus) return l;
const pos = etat.positions[coin];
if (pos) {
if (Number.isInteger(pos.levier_max) && l.levier > pos.levier_max) {
return {
refus: "levier x" + l.levier + " au-dessus du plafond de " + coin + " (x" + pos.levier_max + ") : la place le refuse"
};
}
const margeAutres = margeUtilisee(etat) - _margePosition(pos);
const margeNeuve = Math.abs(pos.taille_signee) * pos.prix_entree / l.levier;
const disponible = equite(etat) - margeAutres - margeNeuve;
if (disponible < -1e-9) {
return {
refus: "levier x" + l.levier + " refusé sur la position ouverte : " + _usd(margeNeuve) + " de marge requis, " + _usd(equite(etat) - margeAutres) + " disponibles"
};
}
pos.levier = l.levier;
}
etat.leviers[coin] = l.levier;
return {
ok: true,
coin: coin,
levier: l.levier
};
}

export function reinitialiser(etat, equiteNeuve) {
const e = _verifierEtat(etat);
if (e) return e;
const cible = equiteNeuve === undefined || equiteNeuve === null ? etat.equite_depart : equiteNeuve;
if (!_nombre(cible) || cible <= 0) return {
refus: "équité de remise à zéro illisible : un nombre de dollars strictement positif est attendu"
};
etat.equite_depart = cible;
etat.solde = cible;
etat.frais_cumules = 0;
etat.pnl_ferme_cumule = 0;
etat.positions = {};
etat.juge_ms = {};
etat.remplissages = [];
etat.nb_reinitialisations += 1;
etat.reinitialise_le_ms = etat.t_courant_ms;
etat.limites = LIMITES_DEMO.slice();
return {
ok: true,
equite_depart: cible,
solde: etat.solde,
nb_reinitialisations: etat.nb_reinitialisations,
reinitialise_le_ms: etat.reinitialise_le_ms,
marks_gardes: Object.keys(etat.marks).sort()
};
}

function _positionInterne(etat, p) {
const latent = _latentPosition(etat, p);
const marge = _margePosition(p);
const m = etat.marks[p.coin];
return {
coin: p.coin,
natif: true,
place_actif: "",
sens: p.taille_signee > 0 ? "long" : "short",
taille: Math.abs(p.taille_signee),
taille_signee: p.taille_signee,
prix_entree: p.prix_entree,
levier: p.levier,
croise: p.croise !== false,
tp: p.tp,
sl: p.sl,
pnl_latent: latent,
valeur: m ? Math.abs(p.taille_signee) * m.prix : null,
prix_liquidation: _prixLiquidation(etat, p),
marge: marge,
rendement: marge > 0 ? latent / marge : null,
mode_marge: p.croise === false ? "isole" : "croise",
simule: true
};
}

export function positionsInternes(etat) {
if (_verifierEtat(etat)) return {};
const out = {};
for (const coin of Object.keys(etat.positions).sort()) out[coin] = _positionInterne(etat, etat.positions[coin]);
return out;
}

export function positions(etat) {
if (_verifierEtat(etat)) return [];
const out = [];
for (const coin of Object.keys(etat.positions).sort()) {
const p = etat.positions[coin];
const m = etat.marks[coin];
const latent = +_latentPosition(etat, p).toFixed(2);
const marge = _margePosition(p);
const liq = _prixLiquidation(etat, p);
out.push({
actif: coin,
sens: p.taille_signee > 0 ? "long" : "court",
taille: Math.abs(p.taille_signee),
taille_signee: p.taille_signee,
prix_entree: p.prix_entree,
levier: p.levier,
pnl_latent: latent,
pnl_non_realise: latent,
prix_liquidation: liq,
sans_prix_liquidation: liq === null,
valeur_position: m ? +(Math.abs(p.taille_signee) * m.prix).toFixed(2) : null,
marge_utilisee: marge,
mode_marge: p.croise === false ? "isole" : "croise",
rendement_sur_fonds: marge > 0 ? latent / marge : null,
place: "",
source: "demo",
tp: p.tp,
sl: p.sl,
simule: true
});
}
return out;
}

export function ordres(etat) {
if (_verifierEtat(etat)) return [];
const out = [];
for (const coin of Object.keys(etat.positions).sort()) {
const p = etat.positions[coin];
const long = p.taille_signee > 0;
const taille = Math.abs(p.taille_signee);
const base = {
actif: coin,
sens: long ? "vente" : "achat",
taille: taille,
taille_initiale: taille,
reduction_seule: true,
declencheur: true,
duree: null,
cloid: null,
condition_declencheur: null,
coin: coin,
side: long ? "A" : "B",
sz: taille,
origSz: taille,
isTrigger: true,
reduceOnly: true,
tif: null,
triggerCondition: null,
origine: "demo"
};
if (p.sl !== null) {
out.push(Object.assign({}, base, {
prix: p.sl,
prix_declencheur: p.sl,
identifiant: p.sl_oid,
horodatage_ms: p.sl_pose_ms,
type: "Stop Market",
role: "sl",
limitPx: p.sl,
triggerPx: p.sl,
oid: p.sl_oid,
timestamp: p.sl_pose_ms,
orderType: "Stop Market"
}));
}
if (p.tp !== null) {
out.push(Object.assign({}, base, {
prix: p.tp,
prix_declencheur: p.tp,
identifiant: p.tp_oid,
horodatage_ms: p.tp_pose_ms,
type: "Take Profit Limit",
role: "tp",
limitPx: p.tp,
triggerPx: p.tp,
oid: p.tp_oid,
timestamp: p.tp_pose_ms,
orderType: "Take Profit Limit"
}));
}
}
return out;
}

export function remplissages(etat) {
if (_verifierEtat(etat)) return [];
return etat.remplissages.map(f => Object.assign({}, f));
}

export function journal(etat) {
return remplissages(etat).reverse();
}

export function remplissagesPage(etat) {
if (_verifierEtat(etat)) return [];
return etat.remplissages.map(f => ({
horodatage_ms: f.quand,
actif: f.coin,
direction: f.sens,
sens: f.sens,
taille: f.taille,
prix: f.prix,
pnl_ferme: f.pnl,
frais: f.frais,
jeton_frais: f.jeton_frais || "USDC",
identifiant_transaction: f.tid,
origine: "demo",
motif_demo: f.motif_demo
}));
}

export function verifierInvariants(etat) {
const e = _verifierEtat(etat);
if (e) return [ e.refus ];
const fautes = [];
let pnl = 0, frais = 0;
const parCoin = {};
let tPrec = -Infinity, tidPrec = 0;
for (const f of etat.remplissages) {
pnl += f.pnl;
frais += f.frais;
const delta = f.cote === "achat" ? f.taille : -f.taille;
parCoin[f.coin] = _arrondirTaille((parCoin[f.coin] || 0) + delta);
if (f.quand < tPrec) fautes.push("remplissage " + f.tid + " daté avant le précédent");
if (f.tid <= tidPrec) fautes.push("tid " + f.tid + " non croissant");
if (f.frais < 0) fautes.push("frais négatifs sur " + f.tid);
tPrec = f.quand;
tidPrec = f.tid;
}
const soldeAttendu = etat.equite_depart + pnl - frais;
if (Math.abs(etat.solde - soldeAttendu) > 1e-6) {
fautes.push("solde " + etat.solde + " différent de départ + pnl - frais = " + soldeAttendu);
}
if (Math.abs(etat.frais_cumules - frais) > 1e-6) fautes.push("frais cumulés " + etat.frais_cumules + " différents de la somme " + frais);
if (Math.abs(etat.pnl_ferme_cumule - pnl) > 1e-6) fautes.push("pnl fermé cumulé " + etat.pnl_ferme_cumule + " différent de la somme " + pnl);
for (const coin in etat.positions) {
const p = etat.positions[coin];
const m = etat.marks[coin];
if (p.taille_signee === 0) fautes.push("position à plat conservée sur " + coin);
if (!m) fautes.push("position sans mark sur " + coin);
if (!Number.isInteger(p.levier) || p.levier < 1) fautes.push("levier illisible sur " + coin);
if (m && p.tp !== null && (p.taille_signee > 0 ? p.tp <= m.prix : p.tp >= m.prix)) fautes.push("TP non déclenché du mauvais côté du mark sur " + coin);
if (m && p.sl !== null && (p.taille_signee > 0 ? p.sl >= m.prix : p.sl <= m.prix)) fautes.push("SL non déclenché du mauvais côté du mark sur " + coin);
if (Math.abs((parCoin[coin] || 0) - p.taille_signee) > 1e-9) {
fautes.push("position " + coin + " (" + p.taille_signee + ") différente du cumul des remplissages (" + (parCoin[coin] || 0) + ")");
}
}
for (const coin in parCoin) {
if (!etat.positions[coin] && Math.abs(parCoin[coin]) > 1e-9) fautes.push("cumul des remplissages non nul sans position sur " + coin);
}
return fautes;
}
