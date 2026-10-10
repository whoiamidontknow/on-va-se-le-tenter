export const NOM = "flux_service";

export const TIRET = "—";

export const ABONNEMENTS_MAX_PAR_SOCKET = 12;

export const MESSAGES_MAX_PAR_FENETRE = 20;

export const FENETRE_CADENCE_S = 10;

export const TAILLE_MESSAGE_MAX_OCTETS = 65536;

export const RESERVE_CADENCE = 4;

export const RATTRAPAGE_PLANCHER_S = 2;

export const RESYNC_PLANCHER_S = 2;

export const RESYNCS_AVANT_DE_LE_DIRE = 3;

export const DUREE_JETON_REPLI_S = 600;

export const GRACE_EXPIRATION_REPLI_S = 30;

export const RENOUVELLEMENT_AVANT_S = 120;

export const INTERVALLE_APRES_ECHEC_S = 20;

export const MARGE_REUTILISATION_S = 30;

export const RETRY_AFTER_MAX_S = 3600;

export const RECUL_RENOUVELLEMENT_MAX_S = 600;

export const MARGE_RENOUVELLEMENT_MIN_S = 5;

export const DUREE_PLAUSIBLE_MIN_S = 30;

export const DUREE_PLAUSIBLE_MAX_S = 3600;

export const RECUL_BASE_S = 1;

export const RECUL_MAX_S = 30;

export const GRAIN_RECUL = .25;

export const DELAI_OUVERTURE_S = 15;

export const SAUT_TEMPS_S = 60;

const TRADES_GARDES = 400;

export const FAITS_PAR_REPONSE = 500;

export const FAITS_GARDES = 1e3;

export const MACHINE_FERME = "ferme";

export const MACHINE_JETON_DEMANDE = "jeton demande";

export const MACHINE_SOCKET_DEMANDE = "socket demande";

export const MACHINE_SOCKET_OUVERT = "socket ouvert";

export const MACHINE_AUTH_ENVOYEE = "auth envoyee";

export const MACHINE_AUTORISE = "autorise";

export const MACHINE_ATTENTE_RECONNEXION = "attente de reconnexion";

export const MACHINE_ARRETE = "arrete";

export const MOTIF_ESSAI_TERMINE = "essai_termine";

export const MOTIF_AUCUN_DROIT = "aucun_droit";

export const MOTIF_HORS_MATRICE = "hors_matrice";

export const MOTIF_CONSTRUCTION = "construction";

export const PHRASE_REPOS = "Flux Ephore au repos.";

export const PHRASE_CONNEXION = "Connexion au flux Ephore en cours...";

export const PHRASE_EN_LIGNE = "Flux Ephore en ligne.";

export const PHRASE_SESSION_EXPIREE = "Session expirée : reconnecte-toi à ton espace membre, puis rouvre le " + "cockpit. Le flux ne peut pas la rouvrir à ta place.";

export const PHRASE_ESSAI_TERMINE = "Ton essai est terminé : le flux du cockpit demande un abonnement actif.";

export const PHRASE_ACCES_RESERVE = "Accès réservé : ton compte n'ouvre pas le flux du cockpit.";

export const PHRASE_CONSTRUCTION = "Cette partie du cockpit est encore en construction : rien à afficher " + "pour l'instant.";

export const PHRASE_VERIFICATION_INDISPONIBLE = "Vérification d'accès indisponible côté Ephore : ce n'est pas un refus, " + "nouvelle tentative dans ";

export const PHRASE_HUB_INJOIGNABLE = "Espace membre injoignable : nouvelle tentative dans ";

export const PHRASE_SERVICE_INJOIGNABLE = "Service Ephore injoignable : nouvelle tentative dans ";

export const PHRASE_LIEN_COUPE = "Lien coupé par le service Ephore : reconnexion dans ";

export const PHRASE_QUOTA_JETONS = "Quota d'accès de l'heure atteint côté Ephore : reprise dans ";

export const PHRASE_RENOUVELLEMENT_RATE = "Renouvellement de l'accès en échec : le flux tient jusqu'à l'expiration " + "en cours, nouvelle tentative dans ";

export const PHRASE_TROU_COUPURE = "Des alertes ont pu être manquées pendant la coupure.";

export const PHRASE_TROU_ANCIEN = "Des alertes plus anciennes ne sont plus tenues par le service : " + "l'historique commence où il commence.";

export const PHRASE_BORNE_ABONNEMENTS = "Borne d'abonnements atteinte (" + ABONNEMENTS_MAX_PAR_SOCKET + " actifs par canal) : désabonne-toi d'un actif avant d'en suivre un autre.";

export const PHRASE_CADENCE = "Trop de demandes d'un coup : celle-ci est ignorée, réessaie dans un " + "instant. Le service ferme les canaux trop bavards.";

export const PHRASE_HORS_UNIVERS = "Actif hors univers d'alertes Ephore : les unités demandées seulement, " + "pas de feu, pas d'alertes, pas de screener.";

export const PHRASE_HORLOGE = "L'horloge de cette machine paraît fausse : le renouvellement de l'accès " + "se cale sur la durée documentée, vérifie l'heure de ton ordinateur.";

export const PHRASE_RESYNCS = "Le flux se resynchronise en boucle : les graphiques peuvent rester " + "datés quelques instants.";

export const PHRASE_COUPURES_PRECOCES = "Le service Ephore coupe le flux juste après l'ouverture : ce n'est pas " + "ton réseau, on réessaie plus lentement, nouvelle tentative dans ";

export const VIE_STABLE_S = 60;

export const COUPURES_PRECOCES_AVANT_DE_LE_DIRE = 3;

function _dict(x) {
return x !== null && typeof x === "object" && !Array.isArray(x);
}

function _a(objet, clef) {
return Object.prototype.hasOwnProperty.call(objet, clef);
}

function _entier(x) {
return typeof x === "number" && Number.isInteger(x);
}

function _msg(e) {
if (e instanceof Error) return e.message || String(e);
return String(e);
}

export function octets_utf8(texte) {
const s = String(texte);
let n = 0;
for (let i = 0; i < s.length; i += 1) {
const c = s.codePointAt(i);
if (c <= 127) n += 1; else if (c <= 2047) n += 2; else if (c <= 65535) n += 3; else {
n += 4;
i += 1;
}
}
return n;
}

function _secondes(x) {
if (typeof x !== "number" || !Number.isFinite(x)) return TIRET;
const v = Math.max(0, Math.round(x));
return v + " s";
}

export function appliquer_delta(etat, unites) {
if (!_dict(etat) || !_dict(unites)) return null;
const nouveau = {};
for (const u of Object.keys(etat)) {
const du = _a(unites, u) ? unites[u] : undefined;
if (_dict(du) && du.retire) continue;
nouveau[u] = etat[u];
}
for (const u of Object.keys(unites)) {
const du = unites[u];
if (!_dict(du)) return null;
if (du.retire) continue;
const anc = _dict(nouveau[u]) ? nouveau[u] : {};
let nb = anc.bougies;
let ni = anc.indicateurs;
if (_a(du, "bougies")) {
nb = _appliquer_bougies(anc.bougies, du.bougies);
if (nb === null) return null;
}
if (_a(du, "indicateurs")) {
ni = _appliquer_indics(anc.indicateurs, du.indicateurs);
if (ni === null) return null;
}
if (!Array.isArray(nb) || !Array.isArray(ni)) return null;
nouveau[u] = {
bougies: nb,
indicateurs: ni
};
}
return nouveau;
}

export function _appliquer_bougies(anciennes, op) {
if (!_dict(op)) return null;
if (_a(op, "remplace")) {
return Array.isArray(op.remplace) ? op.remplace : null;
}
if (!Array.isArray(anciennes)) return null;
for (const clef of [ "retire_avant", "chg", "ajout", "n" ]) {
if (!_a(op, clef)) return null;
}
const k = op.retire_avant;
if (!_entier(k) || k < 0 || k > anciennes.length) return null;
const b = anciennes.slice(k);
const bornes = b.length;
if (!Array.isArray(op.chg) || !Array.isArray(op.ajout)) return null;
for (const ch of op.chg) {
if (!Array.isArray(ch) || ch.length !== 2) return null;
const i = ch[0];
if (!_entier(i) || i < 0 || i >= bornes) return null;
b[i] = ch[1];
}
for (const bougie of op.ajout) b.push(bougie);
if (b.length !== op.n) return null;
if (b.length === 0) return op.n === 0 ? b : null;
if (!_dict(b[0]) || !_dict(b[b.length - 1])) return null;
if (b[0].t !== op.t0 || b[b.length - 1].t !== op.tf) return null;
return b;
}

export function _appliquer_indics(anciens, op) {
if (!_dict(op)) return null;
if (_a(op, "remplace")) {
return Array.isArray(op.remplace) ? op.remplace : null;
}
if (!Array.isArray(anciens) || !_a(op, "ops") || !_a(op, "n")) return null;
if (!Array.isArray(op.ops)) return null;
const n = [];
for (const o of op.ops) {
if (Array.isArray(o)) {
if (o.length !== 2) return null;
const d = o[0];
const c = o[1];
if (!_entier(d) || !_entier(c) || d < 0 || c < 1 || d + c > anciens.length) return null;
for (let i = d; i < d + c; i += 1) n.push(anciens[i]);
} else if (_dict(o) && _a(o, "+")) {
n.push(o["+"]);
} else if (_dict(o) && _entier(o["%"])) {
const j = o["%"];
if (j < 0 || j >= anciens.length) return null;
const base = anciens[j];
if (!_dict(base)) return null;
const copie = Object.assign({}, base);
const champs = _dict(o.champs) ? o.champs : {};
for (const clef of Object.keys(champs)) copie[clef] = champs[clef];
const listes = _dict(o.listes) ? o.listes : {};
for (const clef of Object.keys(listes)) {
const src = base[clef];
const dl = listes[clef];
if (!Array.isArray(src) || !_dict(dl)) return null;
const ka = dl.retire_avant;
const p = dl.garde;
if (!_entier(ka) || !_entier(p) || ka < 0 || p < 0) return null;
const ajout = Array.isArray(dl.ajout) ? dl.ajout : [];
const l = src.slice(ka, ka + p).concat(ajout);
if (l.length !== dl.n) return null;
copie[clef] = l;
}
n.push(copie);
} else {
return null;
}
}
if (n.length !== op.n) return null;
return n;
}

export function lire_reponse_jeton(r) {
if (!_dict(r)) {
return {
issue: "reessai",
statut: null,
motif: null,
erreur: "réponse illisible du hub",
phrase: PHRASE_HUB_INJOIGNABLE
};
}
const donnees = _dict(r.donnees) ? r.donnees : r;
const statut = _entier(r.statut) ? r.statut : _entier(donnees.statut) ? donnees.statut : null;
const jeton = typeof donnees.jeton === "string" ? donnees.jeton : null;
const exp = typeof donnees.exp === "number" ? donnees.exp : null;
if (jeton && (statut === null || statut === 200)) {
return {
issue: "jeton",
statut: statut === null ? 200 : statut,
motif: null,
jeton: jeton,
exp: exp,
phrase: null
};
}
const motif = typeof donnees.motif === "string" ? donnees.motif : null;
if (statut === 401) {
return {
issue: "arret",
statut: statut,
motif: motif,
phrase: PHRASE_SESSION_EXPIREE
};
}
if (statut === 403) {
let phrase = PHRASE_ACCES_RESERVE;
if (motif === MOTIF_ESSAI_TERMINE) phrase = PHRASE_ESSAI_TERMINE; else if (motif === MOTIF_CONSTRUCTION) phrase = PHRASE_CONSTRUCTION;
return {
issue: "arret",
statut: statut,
motif: motif,
phrase: phrase
};
}
if (statut === 429) {
const brutRa = _entier(r.retryAfter) ? r.retryAfter : _entier(donnees.retryAfter) ? donnees.retryAfter : _entier(donnees.retry_after_s) ? donnees.retry_after_s : null;
const attente_s = brutRa !== null && brutRa > 0 ? Math.min(RETRY_AFTER_MAX_S, brutRa) : null;
return {
issue: "reessai",
statut: statut,
motif: motif,
attente_s: attente_s,
phrase: PHRASE_QUOTA_JETONS
};
}
if (statut === 503 || statut === 500) {
return {
issue: "reessai",
statut: statut,
motif: motif,
phrase: PHRASE_VERIFICATION_INDISPONIBLE
};
}
if (statut !== null) {
return {
issue: "reessai",
statut: statut,
motif: motif,
phrase: PHRASE_VERIFICATION_INDISPONIBLE
};
}
const erreur = typeof r.erreur === "string" ? r.erreur : typeof donnees.erreur === "string" ? donnees.erreur : "réponse sans jeton";
return {
issue: "reessai",
statut: null,
motif: null,
erreur: erreur,
phrase: PHRASE_HUB_INJOIGNABLE
};
}

export function verdict_adresse(url) {
const s = String(url === null || url === undefined ? "" : url).trim();
if (!s) {
return "adresse du service absente : le flux ne devine pas où joindre " + "le service Ephore";
}
if (!/^wss:\/\/[^\s]+$/.test(s)) {
return "adresse du service refusée (" + s + ") : le canal du cockpit " + "membres est en wss uniquement, jamais en clair";
}
if (s.includes("?") || s.includes("#")) {
return "adresse du service refusée (" + s + ") : ni requête ni fragment " + "dans l'adresse d'un canal, le jeton voyage dans le premier message";
}
if (s.toLowerCase().includes("jeton")) {
return "adresse du service refusée : un jeton ne voyage JAMAIS dans une " + "adresse (leçon du bloquant 4 du service)";
}
return "";
}

export class FluxService {
constructor({url_service: url_service, demander_jeton: demander_jeton, ouvrir_socket: ouvrir_socket, maintenant: maintenant = null, journal: journal = null, alea: alea = null, abonnements_max: abonnements_max = ABONNEMENTS_MAX_PAR_SOCKET, messages_max_par_fenetre: messages_max_par_fenetre = MESSAGES_MAX_PAR_FENETRE, fenetre_cadence_s: fenetre_cadence_s = FENETRE_CADENCE_S} = {}) {
if (typeof demander_jeton !== "function" || typeof ouvrir_socket !== "function") {
throw new Error("flux service : les deux fabriques demander_jeton() et " + "ouvrir_socket(url) doivent être injectées au constructeur. Ce " + "module ne crée AUCUNE connexion lui-même.");
}
const verdict = verdict_adresse(url_service);
if (verdict) throw new Error("flux service : " + verdict);
this.url_service = String(url_service).trim();
this._demander_jeton = demander_jeton;
this._ouvrir_socket = ouvrir_socket;
this.horloge = typeof maintenant === "function" ? maintenant : () => Date.now() / 1e3;
this._journal = typeof journal === "function" ? journal : () => {};
this._alea = typeof alea === "function" ? alea : () => Math.random();
this.abonnements_max = Math.trunc(abonnements_max);
this.messages_max_par_fenetre = Math.trunc(messages_max_par_fenetre);
this.fenetre_cadence_s = Number(fenetre_cadence_s);
this._jeton = null;
this._exp = null;
this._grace_s = GRACE_EXPIRATION_REPLI_S;
this._sub = null;
this._duree_utile_s = null;
this._prochain_renouvellement = null;
this._renouvellement_en_vol = false;
this._jeton_confirme = false;
this._attente_dite = false;
this._echecs_renouvellement = 0;
this._horloge_suspecte = false;
this._machine = MACHINE_FERME;
this._machine_depuis = null;
this._veut = false;
this._arrete = false;
this._raison_arret = null;
this._phrase = PHRASE_REPOS;
this._ws = null;
this._file = [];
this._panne_ws = null;
this._jeton_en_vol = false;
this._tentatives = 0;
this._recul_s = 0;
this._prochain_essai = null;
this._dernier_pompage = null;
this._autorise_depuis = null;
this._coupures_precoces = 0;
this._souhaits = new Map;
this._abonnements = new Map;
this._unitesServies = null;
this._regarde = null;
this._actifs = new Map;
this._resyncs = new Map;
this._alertes = {
version: 0,
plancher: 0,
faits: [],
quand: null,
perimetre: null,
note: null,
tronquees: false
};
this._trades_par_actif = new Map;
this._fonds = new Set;
this._refus_fond = new Map;
this._faits_vus = new Set;
this._screener = null;
this._impulsion = null;
this._battement = null;
this._trou = null;
this._prochain_rattrapage = 0;
this._instants_messages = [];
this._anomalies = [];
this._abonnes_etat = [];
}
_dire(phrase) {
this._journal("flux service : " + phrase);
}
_anomalie(phrase) {
this._anomalies.push({
quand: this.horloge(),
phrase: String(phrase)
});
if (this._anomalies.length > 30) this._anomalies.shift();
this._dire(phrase);
}
_machine_devient(etat, pourquoi) {
if (this._machine === etat) return;
this._machine = etat;
this._machine_depuis = this.horloge();
this._dire("état " + etat + (pourquoi ? " (" + pourquoi + ")" : ""));
}
unitesServies() {
return this._unitesServies ? this._unitesServies.slice() : null;
}
etat() {
const vu = this._regarde;
const e = vu !== null ? this._actifs.get(vu) : null;
const abonnements = {};
for (const [actif, a] of this._abonnements) {
abonnements[actif] = {
accepte: a.accepte,
raison: a.raison,
unites: a.unites.slice(),
etage: a.etage
};
}
const souhaits = {};
for (const [actif, u] of this._souhaits) souhaits[actif] = u.slice();
const actifs = {};
for (const [actif, s] of this._actifs) {
actifs[actif] = {
actif: s.actif,
seq: s.seq,
graphiques: s.graphiques,
feux: s.feux,
etage: s.etage,
version: s.version,
quand: s.quand,
perime: s.perime
};
}
return {
machine: this._machine,
coupures_precoces: this._coupures_precoces,
en_ligne: this._machine === MACHINE_AUTORISE,
arrete: this._arrete,
raison_arret: this._raison_arret,
phrase: this._phrase,
sub: this._sub,
unites_servies: this.unitesServies(),
regarde: vu,
graphiques: e ? e.graphiques : {},
feux: e ? e.feux : {},
etage: e ? e.etage : null,
version: e ? e.version : TIRET,
quand: e ? e.quand : TIRET,
seq: e ? e.seq : null,
perime: e ? e.perime : false,
actifs: actifs,
abonnements: abonnements,
souhaits: souhaits,
trades: this._trades_de(vu),
fonds: [ ...this._fonds ],
refus_fond: Object.fromEntries(this._refus_fond),
alertes: {
version: this._alertes.version,
plancher: this._alertes.plancher,
quand: this._alertes.quand === null ? TIRET : this._alertes.quand,
faits: this._alertes.faits,
perimetre: this._alertes.perimetre,
note: this._alertes.note,
tronquees: this._alertes.tronquees
},
screener: this._screener,
impulsion: this._impulsion,
battement: this._battement,
trou: this._trou,
anomalies: this._anomalies.slice(),
prochain_essai_dans_s: this._prochain_essai === null ? null : Math.max(0, this._prochain_essai - this.horloge())
};
}
sur_etat(rappel) {
if (typeof rappel !== "function") {
return () => {};
}
this._abonnes_etat.push(rappel);
try {
rappel(this.etat());
} catch (e) {
this._anomalie("un lecteur d'état a levé : " + _msg(e));
}
return () => {
const i = this._abonnes_etat.indexOf(rappel);
if (i >= 0) this._abonnes_etat.splice(i, 1);
};
}
_prevenir() {
if (this._abonnes_etat.length === 0) return;
const e = this.etat();
for (const rappel of this._abonnes_etat.slice()) {
try {
rappel(e);
} catch (err) {
this._anomalie("un lecteur d'état a levé : " + _msg(err));
}
}
}
_phrase_devient(phrase) {
this._phrase = String(phrase);
}
_place_cadence(interne) {
const maintenant = this.horloge();
const limite = maintenant - this.fenetre_cadence_s;
this._instants_messages = this._instants_messages.filter(t => t > limite);
const plafond = interne ? this.messages_max_par_fenetre : Math.max(1, this.messages_max_par_fenetre - RESERVE_CADENCE);
if (this._instants_messages.length >= plafond) return false;
this._instants_messages.push(maintenant);
return true;
}
_envoyer(objet, interne) {
if (this._ws === null) {
return {
refus: "canal fermé : rien n'est envoyé"
};
}
if (this._machine !== MACHINE_AUTORISE && objet.type !== "auth") {
return {
refus: "rien n'est demandé avant l'authentification"
};
}
if (!this._place_cadence(interne === true)) {
return {
refus: PHRASE_CADENCE
};
}
const texte = JSON.stringify(objet);
const taille = octets_utf8(texte);
if (taille > TAILLE_MESSAGE_MAX_OCTETS) {
return {
refus: "message trop gros (" + taille + " octets, " + TAILLE_MESSAGE_MAX_OCTETS + " au plus)"
};
}
try {
this._ws.envoyer(texte);
} catch (e) {
const phrase = "envoi impossible : " + _msg(e);
this._panne_ws = phrase;
return {
refus: phrase
};
}
return {
ok: true
};
}
async demarrer() {
if (this._arrete) {
return {
refus: this._phrase
};
}
this._veut = true;
this._dernier_pompage = this.horloge();
await this._cycle();
this._prevenir();
return {
ok: true,
machine: this._machine
};
}
arreter(phrase) {
this._veut = false;
this._fermer_canal(phrase || "flux arrêté par la page");
this._machine_devient(MACHINE_FERME, "arrêt demandé");
this._phrase_devient(PHRASE_REPOS);
this._prevenir();
return {
ok: true
};
}
reprendre() {
this._arrete = false;
this._raison_arret = null;
this._tentatives = 0;
this._recul_s = 0;
this._prochain_essai = null;
this._dire("reprise demandée par la page après un arrêt définitif");
return this.demarrer();
}
_arret_definitif(raison, phrase) {
this._arrete = true;
this._veut = false;
this._raison_arret = raison;
this._phrase_devient(phrase);
this._fermer_canal("arrêt définitif : " + raison);
this._machine_devient(MACHINE_ARRETE, raison);
}
_fermer_canal(pourquoi) {
const ws = this._ws;
this._ws = null;
this._file = [];
this._panne_ws = null;
this._abonnements.clear();
for (const s of this._actifs.values()) {
s.seq = null;
s.perime = true;
}
if (ws !== null) {
try {
if (typeof ws.fermer === "function") ws.fermer();
} catch (e) {
this._dire("fermeture du canal : " + _msg(e));
}
this._dire("canal fermé (" + pourquoi + ")");
}
}
async _cycle() {
if (!this._veut || this._arrete) return;
const maintenant = this.horloge();
if (this._prochain_essai !== null && maintenant < this._prochain_essai) {
return;
}
this._prochain_essai = null;
if (this._jeton === null) {
await this._obtenir_jeton(false);
return;
}
if (this._ws === null) {
this._ouvrir();
return;
}
}
async _obtenir_jeton(renouvellement) {
if (this._jeton_en_vol) return;
this._jeton_en_vol = true;
if (!renouvellement) {
this._machine_devient(MACHINE_JETON_DEMANDE, "jeton demandé au hub");
this._phrase_devient(PHRASE_CONNEXION);
}
let brut;
try {
brut = await this._demander_jeton();
} catch (e) {
brut = {
erreur: _msg(e)
};
}
this._jeton_en_vol = false;
const lu = lire_reponse_jeton(brut);
if (lu.issue === "jeton") {
this._attente_dite = false;
this._noter_jeton(lu.jeton, lu.exp);
if (renouvellement) {
const r = this._envoyer({
type: "auth",
jeton: this._jeton
}, true);
if (r.refus) {
this._anomalie("renouvellement non envoyé : " + r.refus);
this._prochain_renouvellement = this.horloge() + INTERVALLE_APRES_ECHEC_S;
} else {
this._dire("jeton renouvelé et renvoyé sur le canal vivant");
}
} else {
this._dire("jeton obtenu du hub");
this._ouvrir();
}
return;
}
if (lu.issue === "arret") {
this._jeton = null;
this._anomalie("accès refusé par le hub (statut " + lu.statut + (lu.motif ? ", motif " + lu.motif : "") + ")");
this._arret_definitif(lu.motif || "statut " + lu.statut, lu.phrase);
return;
}
const dit = lu.statut === null ? lu.erreur || "hub injoignable" : "statut " + lu.statut;
if (renouvellement) {
this._echecs_renouvellement += 1;
const attenteR = lu.attente_s !== null && lu.attente_s !== undefined ? lu.attente_s : Math.min(RECUL_RENOUVELLEMENT_MAX_S, INTERVALLE_APRES_ECHEC_S * Math.pow(2, this._echecs_renouvellement - 1));
this._prochain_renouvellement = this.horloge() + attenteR;
this._anomalie("renouvellement du jeton en échec (" + dit + ") : la session vit jusqu'à l'expiration en cours, " + "nouvelle tentative dans " + _secondes(attenteR));
this._phrase_devient(PHRASE_RENOUVELLEMENT_RATE + _secondes(attenteR) + ".");
return;
}
this._jeton = null;
const attente = lu.attente_s !== null && lu.attente_s !== undefined ? this._reculer_a(lu.attente_s) : this._reculer();
this._anomalie("jeton indisponible (" + dit + ") : nouvelle tentative dans " + _secondes(attente));
this._phrase_devient(lu.phrase + _secondes(attente) + ".");
this._machine_devient(MACHINE_ATTENTE_RECONNEXION, "jeton indisponible");
}
_noter_jeton(jeton, exp) {
this._jeton = jeton;
this._jeton_confirme = false;
this._echecs_renouvellement = 0;
this._exp = typeof exp === "number" && Number.isFinite(exp) ? exp : null;
const maintenant = this.horloge();
let duree = null;
if (this._exp !== null) duree = this._exp - maintenant;
if (duree === null || duree < DUREE_PLAUSIBLE_MIN_S || duree > DUREE_PLAUSIBLE_MAX_S) {
if (this._exp !== null && !this._horloge_suspecte) {
this._horloge_suspecte = true;
this._anomalie("durée apparente du jeton hors bornes (" + Math.round(duree) + " s) : horloge de cette machine " + "probablement fausse, renouvellement calé sur " + DUREE_JETON_REPLI_S + " s");
}
duree = DUREE_JETON_REPLI_S;
}
this._duree_utile_s = duree;
this._prochain_renouvellement = maintenant + Math.max(MARGE_RENOUVELLEMENT_MIN_S, duree - RENOUVELLEMENT_AVANT_S);
}
_ouvrir() {
if (this._ws !== null) return;
if (this._arrete || !this._veut) return;
this._machine_devient(MACHINE_SOCKET_DEMANDE, "ouverture du canal");
this._phrase_devient(PHRASE_CONNEXION);
let ws;
try {
ws = this._ouvrir_socket(this.url_service);
} catch (e) {
const attente = this._reculer();
this._anomalie("ouverture du canal impossible : " + _msg(e) + " ; nouvelle tentative dans " + _secondes(attente));
this._phrase_devient(PHRASE_SERVICE_INJOIGNABLE + _secondes(attente) + ".");
this._machine_devient(MACHINE_ATTENTE_RECONNEXION, "canal injoignable");
return;
}
if (ws === null || ws === undefined || typeof ws.envoyer !== "function") {
const attente = this._reculer();
this._anomalie("la fabrique de canal n'a pas rendu d'objet à envoyer() ;" + " nouvelle tentative dans " + _secondes(attente));
this._phrase_devient(PHRASE_SERVICE_INJOIGNABLE + _secondes(attente) + ".");
this._machine_devient(MACHINE_ATTENTE_RECONNEXION, "canal sans envoyer()");
return;
}
this._ws = ws;
this._panne_ws = null;
ws.surOuverture = () => {
if (this._ws === ws) this._file.push({
_quoi: "ouvert"
});
};
ws.surMessage = texte => {
if (this._ws === ws) this._file.push({
_quoi: "trame",
texte: texte
});
};
ws.surPanne = phrase => {
if (this._ws === ws) this._file.push({
_quoi: "panne",
phrase: String(phrase || "panne du canal")
});
};
ws.surFermeture = phrase => {
if (this._ws === ws) this._file.push({
_quoi: "ferme",
phrase: String(phrase || "canal fermé")
});
};
}
_envoyer_auth() {
const r = this._envoyer({
type: "auth",
jeton: this._jeton
}, true);
if (r.refus) {
this._anomalie("auth non envoyée : " + r.refus);
this._perdre_canal("auth impossible : " + r.refus);
return;
}
this._machine_devient(MACHINE_AUTH_ENVOYEE, "jeton envoyé dans le premier " + "message, jamais dans l'adresse");
}
_reculer_a(secondes) {
this._tentatives += 1;
this._attente_dite = true;
let attente = Number(secondes);
if (!Number.isFinite(attente) || attente < RECUL_BASE_S) attente = RECUL_BASE_S;
if (attente > RETRY_AFTER_MAX_S) attente = RETRY_AFTER_MAX_S;
this._recul_s = attente;
this._prochain_essai = this.horloge() + attente;
return attente;
}
_reculer() {
this._tentatives += 1;
this._attente_dite = false;
const base = Math.min(RECUL_MAX_S, RECUL_BASE_S * Math.pow(2, this._tentatives - 1));
let grain;
try {
grain = Number(this._alea());
} catch (e) {
grain = .5;
}
if (!Number.isFinite(grain) || grain < 0 || grain > 1) grain = .5;
const attente = base * (1 - GRAIN_RECUL + 2 * GRAIN_RECUL * grain);
this._recul_s = attente;
this._prochain_essai = this.horloge() + attente;
return attente;
}
_perdre_canal(phrase) {
this._fermer_canal(phrase);
if (this._arrete || !this._veut) {
this._machine_devient(MACHINE_FERME, "canal perdu, la page ne veut plus");
return;
}
const reutilisable = this._jeton !== null && this._jeton_confirme && this._prochain_renouvellement !== null && this.horloge() < this._prochain_renouvellement - MARGE_REUTILISATION_S;
if (reutilisable) {
this._jeton_confirme = false;
} else {
this._jeton = null;
this._prochain_renouvellement = null;
}
const vecu = this._autorise_depuis === null ? null : this.horloge() - this._autorise_depuis;
this._autorise_depuis = null;
if (vecu !== null && vecu < VIE_STABLE_S) {
this._coupures_precoces += 1;
this._tentatives = Math.max(this._tentatives, this._coupures_precoces - 1);
} else if (vecu !== null) {
this._coupures_precoces = 0;
}
const attente = this._reculer();
const precoce = this._coupures_precoces >= COUPURES_PRECOCES_AVANT_DE_LE_DIRE;
this._phrase_devient((precoce ? PHRASE_COUPURES_PRECOCES : PHRASE_LIEN_COUPE) + _secondes(attente) + ".");
this._anomalie("canal perdu (" + phrase + ")" + (vecu !== null && vecu < VIE_STABLE_S ? " " + _secondes(vecu) + " après l'ouverture, " + this._coupures_precoces + "e coupure précoce d'affilée" : "") + " : " + (reutilisable ? "reconnexion avec le jeton en main dans " : "nouveau jeton et reconnexion dans ") + _secondes(attente));
this._machine_devient(MACHINE_ATTENTE_RECONNEXION, "canal perdu");
}
regarder(actif) {
const nom = String(actif === null || actif === undefined ? "" : actif).trim();
if (!nom) return {
refus: "regarder : actif absent"
};
this._regarde = nom;
this._fonds.delete(nom);
const ab = this._abonnements.get(nom);
if (ab && ab.accepte && ab.etage && ab.etage.etage === "froid") {
this._phrase_devient(typeof ab.etage.phrase === "string" ? nom + " : " + ab.etage.phrase : PHRASE_HORS_UNIVERS);
} else if (this._machine === MACHINE_AUTORISE && typeof this._phrase === "string" && this._phrase.indexOf(" : hors univers") > 0 && this._phrase.indexOf(nom + " : ") !== 0) {
this._phrase_devient(PHRASE_EN_LIGNE);
}
this._dire("actif regardé : " + nom);
this._prevenir();
return {
ok: true
};
}
abonner(actif, unites, options) {
const nom = String(actif === null || actif === undefined ? "" : actif).trim();
const fond = !!(options && options.fond === true);
if (!nom) return {
refus: "abonner : actif absent"
};
if (!/^[A-Za-z0-9:_.-]{1,32}$/.test(nom)) {
return {
refus: "abonner : actif hors format (" + nom + ") : 1 a 32 " + "caractères parmi lettres, chiffres, « : », « _ », " + "« . » et « - »"
};
}
const liste = Array.isArray(unites) ? unites.filter(u => typeof u === "string" && u) : [];
if (liste.length === 0) {
return {
refus: "abonner : au moins une unité est attendue"
};
}
const propres = [ ...new Set(liste) ];
if (!this._souhaits.has(nom) && this._souhaits.size >= this.abonnements_max) {
return {
refus: PHRASE_BORNE_ABONNEMENTS
};
}
this._souhaits.set(nom, propres);
if (fond && this._regarde !== nom) this._fonds.add(nom); else this._fonds.delete(nom);
if (this._regarde === null && !fond) this._regarde = nom;
this._dire("abonnement souhaité : " + nom + " [" + propres.join(", ") + "]" + (fond ? " (de fond)" : ""));
if (this._machine !== MACHINE_AUTORISE) {
this._prevenir();
return {
ok: true,
differe: true
};
}
const r = this._envoyer({
type: "abonner",
actif: nom,
unites: propres
}, false);
if (r.refus) {
this._phrase_devient(r.refus);
this._prevenir();
return {
refus: r.refus,
souhait_garde: true
};
}
this._prevenir();
return {
ok: true,
differe: false
};
}
desabonner(actif) {
const nom = String(actif === null || actif === undefined ? "" : actif).trim();
if (!nom) return {
refus: "desabonner : actif absent"
};
const avait = this._souhaits.delete(nom);
this._actifs.delete(nom);
this._resyncs.delete(nom);
this._fonds.delete(nom);
this._trades_par_actif.delete(nom);
if (this._regarde === nom) {
const restants = [ ...this._souhaits.keys() ];
this._regarde = restants.length ? restants[0] : null;
}
if (this._machine !== MACHINE_AUTORISE) {
this._abonnements.delete(nom);
this._prevenir();
return {
ok: true,
differe: true,
etait_souhaite: avait
};
}
const r = this._envoyer({
type: "desabonner",
actif: nom
}, false);
this._prevenir();
if (r.refus) return {
refus: r.refus
};
return {
ok: true,
etait_souhaite: avait
};
}
resync(actif, pourquoi) {
const nom = String(actif === null || actif === undefined ? "" : actif).trim();
if (!nom) return {
refus: "resync : actif absent"
};
if (!this._souhaits.has(nom)) {
return {
refus: "resync d'un actif non suivi : " + nom
};
}
const maintenant = this.horloge();
const suivi = this._resyncs.get(nom) || {
dernier: null,
suite: 0
};
if (suivi.dernier !== null && maintenant - suivi.dernier < RESYNC_PLANCHER_S) {
return {
refus: "resync trop rapproché pour " + nom + " : au plus un " + "par " + RESYNC_PLANCHER_S + " s"
};
}
if (this._machine !== MACHINE_AUTORISE) {
return {
refus: "resync : le canal n'est pas authentifié"
};
}
const r = this._envoyer({
type: "resync",
actif: nom
}, true);
if (r.refus) return {
refus: r.refus
};
suivi.dernier = maintenant;
suivi.suite += 1;
this._resyncs.set(nom, suivi);
this._dire("resync demandé pour " + nom + (pourquoi ? " (" + pourquoi + ")" : ""));
if (suivi.suite >= RESYNCS_AVANT_DE_LE_DIRE) {
this._phrase_devient(PHRASE_RESYNCS);
this._anomalie("resync numéro " + suivi.suite + " d'affilée pour " + nom + " sans instantane valide entre-temps");
}
return {
ok: true
};
}
rattraper(demande) {
const d = _dict(demande) ? demande : {};
const message = {
type: "depuis"
};
if (_a(d, "alertes") || Object.keys(d).length === 0) {
const n = _entier(d.alertes) && d.alertes >= 0 ? d.alertes : this._alertes.version;
message.alertes = n;
}
if (d.screener === true || Object.keys(d).length === 0) message.screener = 0; else if (_entier(d.screener) && d.screener >= 0) message.screener = d.screener;
if (d.impulsion === true || Object.keys(d).length === 0) message.impulsion = 0; else if (_entier(d.impulsion) && d.impulsion >= 0) message.impulsion = d.impulsion;
if (Object.keys(message).length === 1) {
return {
refus: "rattraper : au moins un volet parmi alertes, " + "screener, impulsion"
};
}
if (this._machine !== MACHINE_AUTORISE) {
return {
refus: "rattraper : le canal n'est pas authentifié"
};
}
const maintenant = this.horloge();
if (maintenant < this._prochain_rattrapage) {
return {
refus: "rattrapage trop rapproché : au plus un par " + RATTRAPAGE_PLANCHER_S + " s (le service en tient un " + "par seconde et par volet)"
};
}
const r = this._envoyer(message, true);
if (r.refus) return {
refus: r.refus
};
this._prochain_rattrapage = maintenant + RATTRAPAGE_PLANCHER_S;
this._dire("rattrapage demandé : " + JSON.stringify(message));
return {
ok: true,
demande: message
};
}
async pomper() {
const maintenant = this.horloge();
if (this._dernier_pompage !== null && maintenant - this._dernier_pompage > SAUT_TEMPS_S) {
const saut = maintenant - this._dernier_pompage;
this._anomalie("saut de temps de " + Math.round(saut) + " s (onglet en " + "veille ?) : une seule tentative franche, pas de rafale");
this._tentatives = 0;
this._recul_s = 0;
if (this._prochain_essai !== null && !this._attente_dite) this._prochain_essai = maintenant;
this._instants_messages = [];
}
this._dernier_pompage = maintenant;
const file = this._file;
this._file = [];
for (const evenement of file) {
if (evenement._quoi === "ouvert") {
this._machine_devient(MACHINE_SOCKET_OUVERT, "canal ouvert");
this._envoyer_auth();
} else if (evenement._quoi === "trame") {
this._trame(evenement.texte);
} else if (evenement._quoi === "panne") {
this._perdre_canal(evenement.phrase);
break;
} else if (evenement._quoi === "ferme") {
this._perdre_canal(evenement.phrase);
break;
}
}
if (this._panne_ws !== null) {
const p = this._panne_ws;
this._panne_ws = null;
this._perdre_canal(p);
}
if (this._machine_depuis !== null && (this._machine === MACHINE_SOCKET_DEMANDE || this._machine === MACHINE_SOCKET_OUVERT || this._machine === MACHINE_AUTH_ENVOYEE) && this.horloge() - this._machine_depuis > DELAI_OUVERTURE_S) {
this._perdre_canal("aucune réponse du service en " + Math.round(this.horloge() - this._machine_depuis) + " s (canal suspendu à l'état " + this._machine + ")");
}
if (this._machine === MACHINE_AUTORISE && this._prochain_renouvellement !== null && this.horloge() >= this._prochain_renouvellement && !this._jeton_en_vol) {
this._prochain_renouvellement = this.horloge() + INTERVALLE_APRES_ECHEC_S;
this._dire("renouvellement du jeton avant expiration");
await this._obtenir_jeton(true);
}
await this._cycle();
this._prevenir();
return {
ok: true,
machine: this._machine
};
}
_trame(texte) {
let m;
try {
m = JSON.parse(String(texte));
} catch (e) {
this._anomalie("trame illisible du service (" + _msg(e) + ")");
return;
}
if (!_dict(m) || typeof m.type !== "string") {
this._anomalie("trame sans type : ignorée");
return;
}
switch (m.type) {
case "auth_ok":
return this._auth_ok(m);

case "refus":
return this._refus(m);

case "abonnement":
return this._abonnement(m);

case "desabonnement":
return this._desabonnement(m);

case "instantane":
return this._instantane(m);

case "delta":
return this._delta(m);

case "alertes":
return this._volet_alertes(m);

case "trades":
return this._trades_entrants(m);

case "screener":
return this._volet_versionne("screener", m);

case "impulsion":
return this._volet_versionne("impulsion", m);

case "battement":
return this._battement_recu(m);

default:
this._anomalie("type de trame inconnu du service : " + m.type);
}
}
_auth_ok(m) {
this._sub = typeof m.sub === "string" ? m.sub : null;
if (typeof m.grace_s === "number" && Number.isFinite(m.grace_s)) {
this._grace_s = m.grace_s;
}
if (typeof m.exp === "number" && Number.isFinite(m.exp)) {
this._exp = m.exp;
const duree = m.exp - this.horloge();
if (duree >= DUREE_PLAUSIBLE_MIN_S && duree <= DUREE_PLAUSIBLE_MAX_S) {
this._duree_utile_s = duree;
this._prochain_renouvellement = this.horloge() + Math.max(MARGE_RENOUVELLEMENT_MIN_S, duree - RENOUVELLEMENT_AVANT_S);
}
} else if (m.exp === null) {
this._prochain_renouvellement = null;
}
this._jeton_confirme = true;
this._echecs_renouvellement = 0;
const etait = this._machine;
this._machine_devient(MACHINE_AUTORISE, "auth_ok reçu");
this._phrase_devient(PHRASE_EN_LIGNE);
this._tentatives = 0;
this._recul_s = 0;
this._prochain_essai = null;
this._autorise_depuis = this.horloge();
if (this._horloge_suspecte) this._phrase_devient(PHRASE_HORLOGE);
if (etait !== MACHINE_AUTORISE) {
for (const [actif, unites] of this._souhaits) {
const r = this._envoyer({
type: "abonner",
actif: actif,
unites: unites
}, true);
if (r.refus) {
this._anomalie("réabonnement de " + actif + " non envoyé : " + r.refus);
}
}
const d = this.rattraper({
alertes: this._alertes.version
});
if (d.refus) this._dire("rattrapage différé : " + d.refus);
}
}
_refus(m) {
const phrase = typeof m.erreur === "string" ? m.erreur : "refus sans phrase";
this._anomalie("refus du service : " + phrase);
}
_abonnement(m) {
const actif = typeof m.actif === "string" ? m.actif : null;
if (actif === null) return;
if (Array.isArray(m.unites_servies)) {
const propres = [];
for (const u of m.unites_servies) {
if (typeof u === "string" && u && !propres.includes(u)) propres.push(u);
}
if (propres.length) this._unitesServies = propres;
}
const unites = Array.isArray(m.unites) ? m.unites.slice() : [];
const etage = _dict(m.etage) ? m.etage : null;
this._abonnements.set(actif, {
accepte: m.accepte === true,
raison: typeof m.raison === "string" ? m.raison : "",
unites: unites,
etage: etage
});
if (m.accepte === true) {
this._dire("abonnement accepté : " + actif + " [" + unites.join(", ") + "] étage " + (etage && etage.etage ? etage.etage : TIRET));
this._refus_fond.delete(actif);
if (etage && etage.etage === "froid" && !this._fonds.has(actif)) {
this._phrase_devient(typeof etage.phrase === "string" ? actif + " : " + etage.phrase : PHRASE_HORS_UNIVERS);
}
} else {
const deFond = this._fonds.has(actif);
this._souhaits.delete(actif);
this._fonds.delete(actif);
this._anomalie("abonnement " + (deFond ? "de fond " : "") + "refusé pour " + actif + " : " + (m.raison || "sans raison dite"));
if (deFond) this._refus_fond.set(actif, this.horloge()); else this._phrase_devient(String(m.raison || PHRASE_BORNE_ABONNEMENTS));
}
}
_desabonnement(m) {
const actif = typeof m.actif === "string" ? m.actif : null;
if (actif === null) return;
this._abonnements.delete(actif);
this._dire("desabonnement confirmé : " + actif + (m.retire === true ? "" : " (n'etait pas abonne)"));
}
_instantane(m) {
const actif = typeof m.actif === "string" ? m.actif : null;
if (actif === null) {
this._anomalie("instantané sans actif : jeté");
return;
}
if (!this._souhaits.has(actif)) {
this._anomalie("instantané d'un actif non suivi (" + actif + ") : jeté");
return;
}
const graphiques = _dict(m.graphiques) ? m.graphiques : null;
let unitesValides = 0, uniteCassee = null;
if (graphiques !== null) {
for (const u of Object.keys(graphiques)) {
const g = graphiques[u];
if (_dict(g) && Array.isArray(g.bougies)) unitesValides += 1; else {
uniteCassee = u;
break;
}
}
}
if (graphiques === null || uniteCassee !== null || unitesValides === 0 && !_dict(m.etage)) {
const precedent = this._actifs.get(actif);
if (precedent) {
precedent.perime = true;
precedent.seq = null;
}
this._anomalie("instantané incomplet pour " + actif + " : jeté (" + (graphiques === null ? "graphiques illisibles" : uniteCassee !== null ? "unité " + uniteCassee + " sans liste de bougies" : "aucune unité et aucun étage") + "), état précédent gardé " + (precedent ? "et marqué périmé" : "(aucun)"));
return;
}
this._actifs.set(actif, {
actif: actif,
seq: _entier(m.seq) ? m.seq : null,
graphiques: graphiques,
feux: _dict(m.feux) ? m.feux : {},
etage: _dict(m.etage) ? m.etage : null,
version: _entier(m.version) ? m.version : TIRET,
quand: typeof m.quand === "number" ? m.quand : TIRET,
perime: false
});
const suivi = this._resyncs.get(actif);
if (suivi) {
suivi.suite = 0;
this._resyncs.set(actif, suivi);
}
if (this._phrase === PHRASE_RESYNCS) this._phrase_devient(PHRASE_EN_LIGNE);
this._dire("instantané reçu pour " + actif + " (seq " + (_entier(m.seq) ? m.seq : TIRET) + ", " + Object.keys(graphiques).length + " unités)");
}
_delta(m) {
const actif = typeof m.actif === "string" ? m.actif : null;
if (actif === null) {
this._anomalie("delta sans actif : jeté (aucune réparation possible)");
return;
}
const s = this._actifs.get(actif);
if (!s) {
this._anomalie("delta pour " + actif + " sans état local : " + (this._souhaits.has(actif) ? "resync demandé" : "actif non suivi, jeté"));
if (this._souhaits.has(actif)) this.resync(actif, "delta sans état local");
return;
}
if (s.actif !== actif) {
this._anomalie("DELTA TRANS-ACTIF refusé : delta " + actif + " contre un état " + s.actif + " ; resync");
this.resync(actif, "delta trans-actif");
return;
}
if (!_entier(m.base) || s.seq === null || m.base !== s.seq) {
this._anomalie("delta refusé pour " + actif + " : base " + (m.base === undefined ? TIRET : m.base) + " alors que le seq possédé est " + (s.seq === null ? TIRET : s.seq) + " ; resync");
this.resync(actif, "base du delta inconnue");
return;
}
const unites = _dict(m.unites) ? m.unites : null;
if (unites === null) {
this._anomalie("delta sans unités pour " + actif + " ; resync");
this.resync(actif, "delta sans unités");
return;
}
let neuf;
try {
neuf = appliquer_delta(s.graphiques, unites);
} catch (e) {
neuf = null;
this._anomalie("application du delta impossible (" + _msg(e) + ")");
}
if (neuf === null) {
this._anomalie("delta incohérent pour " + actif + " : rien n'est réparé, resync demandé");
this.resync(actif, "delta incohérent");
return;
}
s.graphiques = neuf;
s.seq = _entier(m.seq) ? m.seq : s.seq;
s.perime = false;
if (_dict(m.feux)) s.feux = m.feux;
if (_dict(m.etage)) s.etage = m.etage;
if (_entier(m.version)) s.version = m.version;
if (typeof m.quand === "number") s.quand = m.quand;
this._actifs.set(actif, s);
}
_trades_entrants(m) {
const actif = typeof m.actif === "string" ? m.actif : null;
const liste = Array.isArray(m.trades) ? m.trades : null;
if (!actif || !liste) {
this._anomalie("trame trades illisible : jetee");
return;
}
if (!this._souhaits.has(actif)) return;
let tampon = this._trades_par_actif.get(actif);
if (!tampon) {
tampon = {
actif: actif,
suite: [],
version: 0,
quand: null
};
this._trades_par_actif.set(actif, tampon);
}
for (const t of liste) {
if (!_dict(t)) continue;
const px = Number(t.px), sz = Number(t.sz), quand = Number(t.t);
if (!(px > 0) || !(sz > 0) || !(quand > 0)) continue;
tampon.suite.push({
t: quand,
px: px,
sz: sz,
sens: t.sens === "achat" ? "achat" : "vente"
});
}
if (tampon.suite.length > TRADES_GARDES) {
tampon.suite.splice(0, tampon.suite.length - TRADES_GARDES);
}
if (_entier(m.version)) tampon.version = m.version;
if (typeof m.quand === "number") tampon.quand = m.quand;
}
_trades_de(actif) {
const t = actif !== null && actif !== undefined ? this._trades_par_actif.get(actif) : null;
if (!t) return {
actif: actif === undefined ? null : actif,
suite: [],
version: 0,
quand: null
};
return {
actif: t.actif,
suite: t.suite,
version: t.version,
quand: t.quand
};
}
_volet_alertes(m) {
const version = _entier(m.version) ? m.version : null;
const plancher = _entier(m.plancher) ? m.plancher : 0;
const faits = Array.isArray(m.faits) ? m.faits : [];
if (version === null) {
this._anomalie("volet alertes sans version : jeté");
return;
}
const notre = this._alertes.version;
if (plancher > 0 && plancher > notre + 1) {
this._marquer_trou(notre === 0 ? PHRASE_TROU_ANCIEN : PHRASE_TROU_COUPURE, "plancher " + plancher + " > version locale " + notre + " + 1");
this._alertes.version = plancher - 1;
}
let ajoutes = 0;
for (const f of faits) {
if (!_dict(f) || !_entier(f.version)) continue;
if (this._faits_vus.has(f.version)) continue;
this._faits_vus.add(f.version);
this._alertes.faits.push(f);
ajoutes += 1;
}
if (ajoutes > 0) {
this._alertes.faits.sort((a, b) => {
const qa = typeof a.quand === "number" ? a.quand : 0;
const qb = typeof b.quand === "number" ? b.quand : 0;
return qa === qb ? a.version - b.version : qa - qb;
});
}
if (this._alertes.faits.length > FAITS_GARDES) {
this._alertes.faits.splice(0, this._alertes.faits.length - FAITS_GARDES);
this._alertes.tronquees = true;
}
while (this._faits_vus.has(this._alertes.version + 1)) {
this._alertes.version += 1;
}
const seuil = this._alertes.version - FAITS_GARDES;
if (seuil > 0) {
for (const v of this._faits_vus) {
if (v <= seuil) this._faits_vus.delete(v);
}
}
this._alertes.plancher = plancher;
this._alertes.quand = typeof m.quand === "number" ? m.quand : TIRET;
if (_dict(m.perimetre)) this._alertes.perimetre = m.perimetre;
if (typeof m.note === "string") this._alertes.note = m.note;
this._dire("alertes : " + ajoutes + " fait(s) neuf(s), version locale " + this._alertes.version + ", plancher " + plancher);
if (faits.length >= FAITS_PAR_REPONSE && this._alertes.version < version) {
const r = this.rattraper({
alertes: this._alertes.version
});
if (r.refus) this._dire("suite du rattrapage différée : " + r.refus);
}
}
_volet_versionne(nom, m) {
const version = _entier(m.version) ? m.version : null;
if (version === null) {
this._anomalie("volet " + nom + " sans version : jeté");
return;
}
const ancien = nom === "screener" ? this._screener : this._impulsion;
if (ancien !== null && _entier(ancien.version) && version < ancien.version) {
this._marquer_trou(PHRASE_TROU_COUPURE, "version " + nom + " en recul (" + ancien.version + " -> " + version + ")");
}
if (nom === "screener") this._screener = m; else this._impulsion = m;
this._dire("volet " + nom + " en version " + version);
}
_battement_recu(m) {
const versions = _dict(m.versions) ? m.versions : {};
this._battement = {
quand: typeof m.quand === "number" ? m.quand : TIRET,
versions: versions,
flux_marche: _dict(m.flux_marche) ? m.flux_marche : null
};
if (_entier(versions.alertes) && versions.alertes < this._alertes.version) {
this._marquer_trou(PHRASE_TROU_COUPURE, "version d'alertes en recul au battement (" + this._alertes.version + " -> " + versions.alertes + ") : le service a redémarré");
this._faits_vus = new Set;
this._alertes.version = versions.alertes;
}
if (_entier(versions.plancher_alertes) && versions.plancher_alertes > 0 && versions.plancher_alertes > this._alertes.version + 1) {
this._marquer_trou(this._alertes.version === 0 ? PHRASE_TROU_ANCIEN : PHRASE_TROU_COUPURE, "plancher " + versions.plancher_alertes + " au battement > version locale " + this._alertes.version + " + 1");
}
if (_entier(versions.alertes) && versions.alertes > this._alertes.version) {
const r = this.rattraper({
alertes: this._alertes.version
});
if (r.refus) this._dire("rattrapage différé : " + r.refus);
}
}
_marquer_trou(phrase, pourquoi) {
this._trou = {
phrase: phrase,
quand: this.horloge(),
pourquoi: pourquoi
};
this._phrase_devient(phrase);
this._anomalie("trou de journal : " + pourquoi);
}
trou_vu() {
this._trou = null;
if (this._machine === MACHINE_AUTORISE) this._phrase_devient(PHRASE_EN_LIGNE);
this._prevenir();
return {
ok: true
};
}
}

export function creer_flux(options) {
return new FluxService(options || {});
}
