"""
╔══════════════════════════════════════════════════════════════╗
║         STAGE HUNTER — Bot de recherche de stage            ║
║         Profil : Admin Sys / Réseaux / Sécurité              ║
║         Nabil Abboud — Paris — Septembre 2026                ║
╚══════════════════════════════════════════════════════════════╝

SOURCES :
  - France Travail (ex Pôle Emploi) — API officielle gratuite
  - Adzuna — API gratuite (500 req/mois en free tier)
  - Jooble — API gratuite (agrégateur : couvre Indeed, HelloWork, APEC, etc.)

UTILISATION :
  1. Copie .env.example → .env et remplis tes clés API
  2. pip install -r requirements.txt
  3. python job_hunter.py
  4. Ouvre rapport_stages.html dans ton navigateur
"""

import os
import sys
import json
import time
import requests
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from report_generator import generate_html_report

# Force UTF-8 sur le terminal Windows (évite UnicodeEncodeError avec les
# caractères spéciaux ═ ║ ╔ ╚ etc.)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# ─── Chargement des variables d'environnement ────────────────────────────────
load_dotenv()

# ─── PROFIL — Modifie ici pour adapter à ton CV ──────────────────────────────
PROFIL = {
    "titre_recherche": "stage CDD administration technicien systèmes réseaux sécurité cybersecurité",
    "localisation": "Île-de-France",
    "rayon_km": 80,  # Couvre toute l'IDF depuis Paris

    # Codes INSEE des départements IDF pour France Travail
    # 75=Paris, 77=Seine-et-Marne, 78=Yvelines, 91=Essonne,
    # 92=Hauts-de-Seine, 93=Seine-Saint-Denis, 94=Val-de-Marne, 95=Val-d'Oise
    "departements_idf": ["75", "77", "78", "91", "92", "93", "94", "95"],

    "mots_cles_positifs": [
        # Compétences techniques — FR
        "linux", "debian", "ubuntu",
        "docker", "conteneur", "container",
        "proxmox", "virtualisation", "vmware", "hyper-v",
        "ansible", "terraform", "automatisation",
        "aws", "cloud", "azure",
        "bash", "shell", "scripting", "python",
        "zabbix", "supervision", "monitoring", "solarwinds",
        "vpn", "ssl", "tls", "firewall", "pare-feu", "pfsense",
        "ssh", "active directory", "windows server",
        "gpo", "dns", "dhcp", "ad ds", "ldap",
        "sécurité", "cybersécurité", "pentest", "soc",
        "réseau", "tcp/ip", "vlan", "switching", "routing",
        "devops", "sre", "infrastructure",
        "servicenow", "powershell",
        # Compétences techniques — EN
        "network", "security", "systems", "virtualization",
        "cloud computing", "containers", "automation",
        "observability", "alerting", "incident response",
        "bgp", "ospf", "network protocols", "load balancer",
        "kubernetes", "k8s", "helm", "ci/cd", "git",
        "vulnerability", "patch management", "hardening",
        "siem", "ids", "ips", "endpoint", "zero trust",
        # Mots-clés de poste — FR
        "administrateur systèmes", "admin sys",
        "ingénieur systèmes", "technicien systèmes",
        "administrateur réseau", "ingénieur réseau",
        "alternance", "stage", "apprentissage", "cdd",
        # Mots-clés de poste — EN
        "sysadmin", "system administrator", "network administrator",
        "network engineer", "infrastructure engineer",
        "security engineer", "cloud engineer",
        "intern", "internship", "apprentice",
    ],
    "mots_cles_negatifs": [
        # Domaines non pertinents
        "comptable", "commercial", "vente", "juridique",
        "rh", "ressources humaines", "marketing",
        "biologie", "médical", "santé",
        "développeur web", "frontend", "graphiste",
        # Localisations hors IDF / hors France
        "canada", "québec", "montréal", "suisse", "belgique", "luxembourg",
    ],

    # ── Pondération du scoring (FR + EN) ─────────────────────
    "poids": {
        # Linux & conteneurs
        "linux": 10,
        "docker": 10,
        "ansible": 8,
        "proxmox": 8,
        "kubernetes": 7,
        "aws": 7,
        "terraform": 7,
        # Windows Server / AD
        "active directory": 10,
        "windows server": 9,
        "gpo": 7,
        "powershell": 7,
        "ad ds": 6,
        "ldap": 5,
        "hyper-v": 5,
        # Supervision & sécu — FR
        "zabbix": 7,
        "cybersécurité": 6,
        "sécurité": 5,
        "soc": 5,
        "pentest": 5,
        "vpn": 5,
        "ssl": 4,
        "pfsense": 4,
        # Supervision & sécu — EN
        "cybersecurity": 6,
        "security": 5,
        "siem": 6,
        "vulnerability": 5,
        "zero trust": 5,
        "endpoint": 4,
        # Réseau — EN
        "network": 5,
        "vlan": 5,
        "firewall": 5,
        # Postes — EN
        "sysadmin": 8,
        "system administrator": 10,
        "network administrator": 10,
        "network engineer": 8,
        "infrastructure engineer": 7,
        "security engineer": 7,
        # Scripting
        "bash": 5,
        "python": 5,
        # DevOps
        "devops": 5,
        "ci/cd": 4,
    }
}


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1 — FRANCE TRAVAIL (ex Pôle Emploi)
#  Docs : https://francetravail.io/produits-et-services/api/offres-emploi
#  Clés gratuites sur : https://francetravail.io/
# ══════════════════════════════════════════════════════════════════════════════

class FranceTravailAPI:
    """Client pour l'API France Travail (anciennement Pôle Emploi)."""

    TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
    API_URL   = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

    def __init__(self):
        self.client_id     = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "")
        self.client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "")
        self.token         = None
        self.token_expiry  = None

    def _get_token(self):
        """Récupère un token OAuth2 (valable 1499 secondes)."""
        if not self.client_id or not self.client_secret:
            print("  ⚠️  France Travail : clés API manquantes dans .env")
            return False

        # Token encore valide
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            return True

        try:
            resp = requests.post(
                self.TOKEN_URL,
                params={"realm": "/partenaire"},
                data={
                    "grant_type":    "client_credentials",
                    "client_id":     self.client_id,
                    "client_secret": self.client_secret,
                    "scope":         "api_offresdemploiv2 o2dsoffre",
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            self.token        = data["access_token"]
            self.token_expiry = datetime.now() + timedelta(seconds=data["expires_in"] - 60)
            return True
        except Exception as e:
            print(f"  ❌ France Travail token : {e}")
            return False

    def search(self, keywords, region_code="11", max_results=50, type_contrat=None):
        """
        Recherche des offres.
        type_contrat : 'CDD', 'CDI', etc. — None pour ne pas filtrer.
                       NB : les stages ne sont PAS un typeContrat dans l'API
                       France Travail (convention de stage ≠ contrat de travail).
                       Pour les stages, utiliser type_contrat=None et ajouter
                       "stage" aux keywords.
        region_code  : code INSEE de la région (11 = Île-de-France)
        motsCles doit rester court (2-4 mots) — des phrases longues retournent 204.
        """
        if not self._get_token():
            return []

        offres   = []
        rang_max = min(max_results, 149)

        try:
            params = {
                "motsCles": keywords,
                "region":   region_code,
                "range":    f"0-{rang_max - 1}",
                "sort":     "0",
            }
            if type_contrat:
                params["typeContrat"] = type_contrat
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept":        "application/json",
            }
            resp = requests.get(self.API_URL, params=params, headers=headers, timeout=15)

            if resp.status_code == 204:
                return []
            resp.raise_for_status()

            data = resp.json()
            raw_offres = data.get("resultats", [])

            label_contrat = "Stage" if type_contrat == "STA" else "CDD"
            for o in raw_offres:
                offres.append({
                    "source":       "France Travail",
                    "id":           o.get("id", ""),
                    "titre":        o.get("intitule", "Sans titre"),
                    "entreprise":   o.get("entreprise", {}).get("nom", "Non précisé"),
                    "lieu":         o.get("lieuTravail", {}).get("libelle", ""),
                    "description":  o.get("description", ""),
                    "date_publi":   o.get("dateCreation", "")[:10] if o.get("dateCreation") else "",
                    "url":          f"https://candidat.francetravail.fr/offres/recherche/detail/{o.get('id', '')}",
                    "type_contrat": label_contrat,
                    "salaire":      o.get("salaire", {}).get("libelle", "Non précisé"),
                    "duree":        o.get("dureeTravailLibelleConverti", ""),
                })

        except requests.exceptions.HTTPError as e:
            print(f"  ❌ France Travail [{type_contrat}] : {e}")
            if e.response is not None:
                print(f"     Détail API : {e.response.text[:300]}")
        except Exception as e:
            print(f"  ❌ France Travail [{type_contrat}] : {e}")

        return offres


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 2 — ADZUNA
#  Docs : https://developer.adzuna.com/
#  Clés gratuites sur : https://developer.adzuna.com/admin/applications
# ══════════════════════════════════════════════════════════════════════════════

class AdzunaAPI:
    """Client pour l'API Adzuna."""

    API_URL = "https://api.adzuna.com/v1/api/jobs/fr/search/{page}"

    def __init__(self):
        self.app_id  = os.getenv("ADZUNA_APP_ID", "")
        self.api_key = os.getenv("ADZUNA_API_KEY", "")

    def search(self, keywords, location="Ile-de-France", max_results=50, contract_type=None):
        """
        Recherche des offres sur Adzuna.
        contract_type : 'contract' pour CDD, None pour stages.
        Adzuna FR ne supporte pas 'internship' — pour les stages laisser
        contract_type=None et inclure 'stage' dans les keywords.
        """
        if not self.app_id or not self.api_key:
            print("  ⚠️  Adzuna : clés API manquantes dans .env")
            return []

        offres   = []
        page     = 1
        per_page = min(50, max_results)
        label_contrat = "CDD" if contract_type == "contract" else "Stage"

        while len(offres) < max_results:
            try:
                params = {
                    "app_id":           self.app_id,
                    "app_key":          self.api_key,
                    "results_per_page": per_page,
                    "what":             keywords,
                    "where":            location,
                    "distance":         PROFIL["rayon_km"],
                    "sort_by":          "date",
                    "content-type":     "application/json",
                }
                if contract_type:
                    params["contract_type"] = contract_type
                resp = requests.get(
                    self.API_URL.format(page=page),
                    params=params,
                    timeout=15
                )
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                if not results:
                    break

                for o in results:
                    offres.append({
                        "source":       "Adzuna",
                        "id":           str(o.get("id", "")),
                        "titre":        o.get("title", "Sans titre"),
                        "entreprise":   o.get("company", {}).get("display_name", "Non précisé"),
                        "lieu":         o.get("location", {}).get("display_name", ""),
                        "description":  o.get("description", ""),
                        "date_publi":   o.get("created", "")[:10] if o.get("created") else "",
                        "url":          o.get("redirect_url", ""),
                        "type_contrat": label_contrat,
                        "salaire":      f"{o.get('salary_min', '')} - {o.get('salary_max', '')} €" if o.get("salary_min") else "Non précisé",
                        "duree":        "",
                    })

                if len(results) < per_page:
                    break
                page += 1
                time.sleep(0.5)

            except Exception as e:
                print(f"  ❌ Adzuna [{contract_type or 'stage'}] page {page} : {e}")
                break

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 3 — JOOBLE
#  Docs : https://jooble.org/api/about
#  Clé gratuite sur : https://jooble.org/api/about (formulaire en bas de page)
#  ⚡ Agrégateur : couvre Indeed, HelloWork, APEC, Cadremploi, Monster, etc.
# ══════════════════════════════════════════════════════════════════════════════

class JoobleAPI:
    """
    Client pour l'API Jooble.
    Jooble est un agrégateur — une seule requête couvre des dizaines de sites
    dont Indeed et HelloWork avec lesquels ils ont des accords partenaires.
    """

    API_URL = "https://jooble.org/api/{api_key}"

    def __init__(self):
        self.api_key = os.getenv("JOOBLE_API_KEY", "")

    def search(self, keywords, location="Paris", max_results=50):
        """
        Recherche des offres sur Jooble.
        L'API attend un POST avec un body JSON simple.
        """
        if not self.api_key:
            print("  ⚠️  Jooble : clé API manquante dans .env")
            return []

        offres = []
        page   = 1

        while len(offres) < max_results:
            try:
                body = {
                    "keywords": keywords,
                    "location": location,
                    "page":     page,
                    # Jooble ne filtre pas par type de contrat via l'API —
                    # le scoring filtrera les offres non pertinentes
                }
                headers = {"Content-Type": "application/json"}
                resp = requests.post(
                    self.API_URL.format(api_key=self.api_key),
                    headers=headers,
                    data=json.dumps(body),
                    timeout=15
                )
                resp.raise_for_status()
                data = resp.json()

                jobs = data.get("jobs", [])
                if not jobs:
                    break

                for o in jobs:
                    # Jooble indique la source d'origine dans le champ "source"
                    source_origine = o.get("source", "")
                    label_source   = f"Jooble ({source_origine})" if source_origine else "Jooble"

                    offres.append({
                        "source":       label_source,
                        "id":           str(o.get("id", "")),
                        "titre":        o.get("title", "Sans titre"),
                        "entreprise":   o.get("company", "Non précisé"),
                        "lieu":         o.get("location", ""),
                        "description":  o.get("snippet", ""),   # Jooble donne un extrait
                        "date_publi":   o.get("updated", "")[:10] if o.get("updated") else "",
                        "url":          o.get("link", ""),
                        "type_contrat": o.get("type", "Non précisé"),
                        "salaire":      o.get("salary", "Non précisé"),
                        "duree":        "",
                    })

                # Jooble pagine par tranches — on s'arrête si moins de résultats
                if len(jobs) < 20:
                    break
                page += 1
                time.sleep(0.5)  # Respect rate limit

            except Exception as e:
                print(f"  ❌ Jooble page {page} : {e}")
                break

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 4 — LINKEDIN JOBS (endpoint non officiel, sans clé)
#  Endpoint : linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
#  Retourne du HTML (pas JSON) → parsé avec regex
#  Pas de description disponible sans requête supplémentaire par offre
# ══════════════════════════════════════════════════════════════════════════════

class LinkedInAPI:
    """
    Scraper pour la page publique LinkedIn Jobs (pas de clé requise).
    Utilise la page de recherche guest /jobs/search/ — accessible sans compte.
    """

    SEARCH_URL = "https://www.linkedin.com/jobs/search/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }

    def _parse_html(self, html, label_contrat):
        """Extrait les offres depuis le HTML retourné par LinkedIn."""
        offres = []
        # Découper le HTML en blocs par div job-search-card
        blocs = re.split(r"(?=<div[^>]+class=\"[^\"]*job-search-card[^\"]*\")", html)
        for bloc in blocs[1:]:  # premier bloc = tout ce qui précède le 1er job
            try:
                id_m   = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', bloc)
                job_id = id_m.group(1) if id_m else ""

                titre_m = re.search(r"base-search-card__title[^>]*>\s*(.*?)\s*</h3>", bloc, re.DOTALL)
                titre   = re.sub(r"\s+", " ", titre_m.group(1)).strip() if titre_m else "Sans titre"
                # Décoder les entités HTML basiques
                titre = titre.replace("&amp;", "&").replace("&#039;", "'").replace("&quot;", '"')

                ent_m      = re.search(r"hidden-nested-link[^>]*>\s*(.*?)\s*</a>", bloc, re.DOTALL)
                entreprise = re.sub(r"\s+", " ", ent_m.group(1)).strip() if ent_m else "Non précisé"
                entreprise = entreprise.replace("&amp;", "&")

                lieu_m = re.search(r"job-search-card__location[^>]*>\s*(.*?)\s*</span>", bloc, re.DOTALL)
                lieu   = lieu_m.group(1).strip() if lieu_m else ""

                url_m = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"]+)"', bloc)
                url   = url_m.group(1).split("?")[0] if url_m else ""

                date_m     = re.search(r'datetime="([^"]+)"', bloc)
                date_publi = date_m.group(1)[:10] if date_m else ""

                if titre and titre != "Sans titre" and url:
                    offres.append({
                        "source":       "LinkedIn",
                        "id":           job_id,
                        "titre":        titre,
                        "entreprise":   entreprise,
                        "lieu":         lieu,
                        "description":  "",  # Non dispo sans requête par offre
                        "date_publi":   date_publi,
                        "url":          url,
                        "type_contrat": label_contrat,
                        "salaire":      "Non précisé",
                        "duree":        "",
                    })
            except Exception:
                continue
        return offres

    def _fetch_description(self, url):
        """
        Récupère la description complète depuis la page de détail d'une offre LinkedIn.
        Les pages /jobs/view/ sont publiques et ne nécessitent pas de compte.
        Retourne une chaîne vide si la récupération échoue.
        """
        if not url:
            return ""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            if resp.status_code != 200 or len(resp.text) < 500:
                return ""
            html = resp.text
            # Plusieurs sélecteurs selon la version de la page LinkedIn
            patterns = [
                r'class="[^"]*show-more-less-html__markup[^"]*"[^>]*>([\s\S]*?)</div>',
                r'class="[^"]*description__text[^"]*"[^>]*>([\s\S]*?)</div>',
                r'<section[^>]+data-max-lines[^>]*>([\s\S]*?)</section>',
            ]
            for pattern in patterns:
                m = re.search(pattern, html)
                if m:
                    desc = re.sub(r'<[^>]+>', ' ', m.group(1))
                    desc = re.sub(r'&nbsp;', ' ', desc)
                    desc = re.sub(r'&amp;', '&', desc)
                    desc = re.sub(r'&lt;', '<', desc)
                    desc = re.sub(r'&gt;', '>', desc)
                    desc = re.sub(r'\s+', ' ', desc).strip()
                    if len(desc) > 80:
                        return desc
            return ""
        except Exception:
            return ""

    def enrich_descriptions(self, offres_linkedin, max_fetch=15):
        """
        Récupère les descriptions pour les offres LinkedIn (description vide par défaut).
        max_fetch : nombre max de requêtes pour éviter le blocage IP.
        Modifie les dicts en place (les mêmes objets sont dans toutes_offres).
        """
        enrichies = 0
        for offre in offres_linkedin:
            if enrichies >= max_fetch:
                break
            if not offre.get("description") and offre.get("url"):
                desc = self._fetch_description(offre["url"])
                if desc:
                    offre["description"] = desc
                    enrichies += 1
                time.sleep(2)  # Délai poli — LinkedIn détecte les rafales
        return enrichies

    def search(self, keywords, location="Ile-de-France", max_results=25, label_contrat="Stage"):
        """
        Recherche des offres LinkedIn (page publique, sans authentification).
        Une seule page est récupérée (~6-10 offres) — LinkedIn bloque la pagination.
        """
        offres = []
        try:
            params = {
                "keywords": keywords,
                "location": location,
            }
            resp = requests.get(self.SEARCH_URL, params=params, headers=self.HEADERS, timeout=15)

            if resp.status_code != 200 or len(resp.text) < 500:
                print(f"  ⚠️  LinkedIn [{keywords}] : réponse vide (status {resp.status_code})")
                return []

            offres = self._parse_html(resp.text, label_contrat)
            time.sleep(2)  # Délai poli entre les requêtes

        except Exception as e:
            print(f"  ❌ LinkedIn [{keywords}] : {e}")

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 5 — SMARTRECRUITERS
#  ATS utilisé par les grandes entreprises françaises : Capgemini, Atos, Sopra
#  Steria, Orange, BNP, Société Générale, Thales, Vinci, AXA...
#  Posting API publique — sans clé pour les offres publiées.
#  Endpoint : api.smartrecruiters.com/v1/companies/{id}/postings
# ══════════════════════════════════════════════════════════════════════════════

class SmartRecruitersAPI:
    """
    Client pour la Posting API publique de SmartRecruiters.
    Interroge une liste d'entreprises françaises IT une par une.
    Sans authentification — les offres publiées sont publiques.
    """

    API_URL = "https://api.smartrecruiters.com/v1/companies/{company}/postings"

    # (Nom affiché, identifiant SmartRecruiters)
    # L'identifiant = ce qui apparaît dans l'URL jobs.smartrecruiters.com/{id}
    # Les 404 sont ignorés silencieusement — liste large sans risque.
    COMPANIES = [
        # ESN & Conseil IT
        ("Capgemini",            "Capgemini"),
        ("Atos",                 "Atos"),
        ("Sopra Steria",         "SopraSteria"),
        ("Alten",                "Alten"),
        ("Altran",               "Altran"),
        ("Accenture",            "Accenture"),
        ("IBM",                  "IBM"),
        ("CGI",                  "CGI"),
        ("Devoteam",             "Devoteam"),
        ("Econocom",             "Econocom"),
        ("Inetum",               "Inetum"),
        ("Aubay",                "Aubay"),
        ("Claranet",             "Claranet"),
        ("Logicalis",            "Logicalis"),
        ("Avanade",              "Avanade"),
        ("DXC Technology",       "DXCTechnology"),
        ("Kyndryl",              "Kyndryl"),
        ("NTT Data",             "NTTData"),
        ("Tata Consultancy",     "TCS"),
        ("Wipro",                "Wipro"),
        ("Infosys",              "Infosys"),
        ("HCL Technologies",     "HCLTech"),
        ("Axians",               "Axians"),
        ("Computacenter",        "Computacenter"),
        ("Atos Worldline",       "Worldline"),
        ("Getronics",            "Getronics"),
        # Telecom & Réseaux
        ("Orange",               "Orange"),
        ("SFR",                  "SFR"),
        ("Bouygues Telecom",     "BouyguesTelecom"),
        ("Nokia",                "Nokia"),
        ("Ericsson",             "Ericsson"),
        ("Cisco",                "Cisco"),
        ("Colt Technology",      "Colt"),
        ("Zayo",                 "Zayo"),
        # Finance & Assurance
        ("BNP Paribas",          "BNPParibas"),
        ("Société Générale",     "SocieteGenerale"),
        ("AXA",                  "AXA"),
        ("Crédit Agricole",      "CreditAgricole"),
        ("Natixis",              "Natixis"),
        ("BPCE",                 "BPCE"),
        ("Malakoff Humanis",     "MalakoffHumanis"),
        ("Generali",             "Generali"),
        ("Allianz",              "Allianz"),
        ("Amundi",               "Amundi"),
        ("La Banque Postale",    "LaBanquePostale"),
        # Industrie & Énergie
        ("Vinci",                "Vinci"),
        ("Engie",                "Engie"),
        ("Thales",               "ThalesGroup"),
        ("Safran",               "Safran"),
        ("Airbus",               "Airbus"),
        ("TotalEnergies",        "TotalEnergies"),
        ("Schneider Electric",   "SchneiderElectric"),
        ("Saint-Gobain",         "SaintGobain"),
        ("Veolia",               "Veolia"),
        ("Suez",                 "Suez"),
        ("Michelin",             "Michelin"),
        ("Renault",              "Renault"),
        ("Stellantis",           "Stellantis"),
        ("Solvay",               "Solvay"),
        # Défense & Aérospatial
        ("Naval Group",          "NavalGroup"),
        ("MBDA",                 "MBDA"),
        ("Dassault Systèmes",    "DassaultSystemes"),
        ("Dassault Aviation",    "DassaultAviation"),
        # Retail & Distribution
        ("Carrefour",            "Carrefour"),
        ("LVMH",                 "LVMH"),
        ("L'Oréal",              "LOreal"),
        ("Sephora",              "Sephora"),
        ("Decathlon",            "Decathlon"),
        # Transport & Logistique
        ("Air France",           "AirFrance"),
        ("SNCF",                 "SNCF"),
        ("Geodis",               "Geodis"),
        ("La Poste",             "LaPoste"),
        # Conseil & Audit
        ("Deloitte",             "DeloitteFrance"),
        ("EY",                   "EY"),
        ("KPMG",                 "KPMG"),
        ("PwC",                  "PwC"),
        ("McKinsey",             "McKinsey"),
        ("BCG",                  "BCG"),
        ("Wavestone",            "Wavestone"),
        ("Mazars",               "Mazars"),
    ]

    # Mots-clés IDF pour filtrer par localisation
    _IDF = {"paris", "île-de-france", "ile-de-france", "hauts-de-seine",
            "seine-saint-denis", "val-de-marne", "val-d'oise", "yvelines",
            "essonne", "seine-et-marne", "clichy", "boulogne", "nanterre",
            "vincennes", "saint-denis", "versailles", "evry"}

    def _is_idf(self, city, region=""):
        """Retourne True si la localisation est en Île-de-France ou non précisée."""
        combined = (city + " " + region).lower()
        if not city:
            return True  # Localisation non précisée → on garde
        return any(k in combined for k in self._IDF)

    def search(self, keywords="", max_results=200, type_emploi="INTERN"):
        """
        Recherche des offres dans chaque entreprise de la liste.
        type_emploi : 'INTERN' pour stages, 'TEMPORARY' pour CDD.
        Échoue silencieusement si l'identifiant entreprise est incorrect (404).
        """
        offres = []
        label = "Stage" if type_emploi == "INTERN" else "CDD"

        for nom, company_id in self.COMPANIES:
            if len(offres) >= max_results:
                break
            try:
                params = {
                    "limit":            10,
                    "offset":           0,
                    "country":          "FRA",
                    "typeOfEmployment": type_emploi,
                }
                if keywords:
                    params["q"] = keywords

                resp = requests.get(
                    self.API_URL.format(company=company_id),
                    params=params,
                    timeout=10
                )
                if resp.status_code in (404, 403):
                    continue
                if resp.status_code != 200:
                    continue

                data = resp.json()
                for o in data.get("content", []):
                    loc    = o.get("location", {}) or {}
                    city   = loc.get("city", "") or ""
                    region = loc.get("region", "") or ""
                    if not self._is_idf(city, region):
                        continue

                    url = (o.get("ref")
                           or f"https://jobs.smartrecruiters.com/{company_id}/{o.get('id', '')}")
                    desc_obj = o.get("jobDescription") or {}
                    desc = desc_obj.get("text", "") if isinstance(desc_obj, dict) else ""

                    offres.append({
                        "source":       "SmartRecruiters",
                        "id":           o.get("id", ""),
                        "titre":        o.get("name", "Sans titre"),
                        "entreprise":   nom,
                        "lieu":         city or "Île-de-France",
                        "description":  desc,
                        "date_publi":   (o.get("releasedDate", "") or "")[:10],
                        "url":          url,
                        "type_contrat": label,
                        "salaire":      "Non précisé",
                        "duree":        "",
                    })

                time.sleep(0.3)

            except Exception:
                continue

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 6 — LEVER
#  ATS utilisé par les startups françaises : BlaBlaCar, Malt, OVHcloud,
#  Back Market, Swile, Shine, Teads, Luko...
#  Postings API 100% publique — aucune clé requise.
#  Endpoint : api.lever.co/v0/postings/{company}?mode=json
# ══════════════════════════════════════════════════════════════════════════════

class LeverAPI:
    """
    Client pour la Postings API publique de Lever.
    Toutes les offres publiées sont accessibles sans authentification.
    L'identifiant entreprise = ce qui apparaît dans jobs.lever.co/{id}.
    """

    API_URL = "https://api.lever.co/v0/postings/{company}"

    # (Nom affiché, identifiant Lever)
    # L'identifiant = ce qui apparaît dans jobs.lever.co/{id}
    COMPANIES = [
        # Licornes & scale-ups françaises
        ("BlaBlaCar",            "blablacar"),
        ("Malt",                 "malt"),
        ("OVHcloud",             "ovhcloud"),
        ("Back Market",          "backmarket"),
        ("Swile",                "swile"),
        ("Shine",                "shine"),
        ("Luko",                 "luko"),
        ("Teads",                "teads"),
        ("Iziwork",              "iziwork"),
        ("Kameleoon",            "kameleoon"),
        ("Alan",                 "alan"),
        ("Lydia",                "lydia"),
        ("Lemon Way",            "lemonway"),
        ("Partoo",               "partoo"),
        ("Yousign",              "yousign"),
        ("Skeepers",             "skeepers"),
        ("Meero",                "meero"),
        ("Akeneo",               "akeneo"),
        ("Talend",               "talend"),
        ("Linkvalue",            "linkvalue"),
        ("Agicap",               "agicap"),
        ("Memo Bank",            "memobank"),
        ("Expensya",             "expensya"),
        ("Brevo",                "brevo"),
        ("Sendinblue",           "sendinblue"),
        ("Mailjet",              "mailjet"),
        ("Vestiaire Collective", "vestiairecollective"),
        ("Younited",             "younited"),
        ("Coexya",               "coexya"),
        ("Theodo",               "theodo"),
        ("Ekino",                "ekino"),
        ("Nuxeo",                "nuxeo"),
        ("Bonitasoft",           "bonitasoft"),
        ("Phenix",               "phenix"),
        ("Greenly",              "greenly"),
        ("Sweep",                "sweep"),
        ("Joko",                 "joko"),
        ("Jellysmack",           "jellysmack"),
        ("Withings",             "withings"),
        ("Deezer",               "deezer"),
        ("Voodoo",               "voodoo"),
        ("Betclic",              "betclic"),
        ("ManoMano",             "manomano"),
        ("Mirakl",               "mirakl"),
        ("JobTeaser",            "jobteaser"),
        ("Leocare",              "leocare"),
        ("Jamespot",             "jamespot"),
        ("Spendesk",             "spendesk"),
        ("PayFit",               "payfit"),
        ("Lucca",                "lucca"),
        # Internationales présentes en France
        ("Zalando",              "zalando"),
        ("N26",                  "n26"),
        ("Spotify",              "spotify"),
        ("Twitch",               "twitch"),
        ("Unity",                "unity"),
        ("Wolt",                 "wolt"),
        ("Deliveroo",            "deliveroo"),
        ("Uber",                 "uber"),
        ("Docusign",             "docusign"),
        ("Cloudinary",           "cloudinary"),
        ("Contentful",           "contentful"),
        ("Figma",                "figma"),
        ("Miro",                 "miro"),
    ]

    _STAGE_MOTS = {"intern", "stage", "alternance", "apprenti", "apprentice",
                   "stagiaire", "trainee"}
    _IDF = {"paris", "île-de-france", "ile-de-france", "hauts-de-seine",
            "nanterre", "boulogne", "clichy", "saint-denis", "vincennes",
            "versailles", "evry", "massy", "puteaux", "levallois",
            "issy", "courbevoie", "la défense", "montreuil", "créteil"}

    # Pays/villes étrangers à rejeter explicitement
    _HORS_FRANCE = {
        "london", "united kingdom", "uk", "england",
        "berlin", "germany", "deutschland",
        "madrid", "spain", "españa",
        "amsterdam", "netherlands", "holland",
        "dublin", "ireland",
        "brussels", "belgium",
        "zurich", "switzerland",
        "milan", "italy",
        "lisbon", "portugal",
        "stockholm", "sweden",
        "copenhagen", "denmark",
        "new york", "san francisco", "chicago", "austin", "seattle",
        "united states", "usa", "canada", "toronto", "montreal",
        "singapore", "sydney", "australia", "dubai", "uae",
    }

    def _is_idf_or_remote(self, location):
        loc = location.lower().strip()
        if not loc:
            return True
        # Rejet explicite si localisation étrangère connue
        if any(ex in loc for ex in self._HORS_FRANCE):
            return False
        # Accepté si France / IDF détecté
        if "france" in loc or any(k in loc for k in self._IDF):
            return True
        # Remote/hybride d'une entreprise de notre liste → on garde
        if "remote" in loc or "télétravail" in loc or "hybrid" in loc or "hybride" in loc:
            return True
        # Localisation inconnue → on garde (conservateur)
        return True

    def search(self, keywords="", max_results=150):
        """
        Récupère les offres de stage/alternance de chaque entreprise.
        Filtre sur IDF/remote et mots de stage dans le titre.
        """
        offres  = []
        kw_list = [k for k in keywords.lower().split() if len(k) > 2] if keywords else []

        for nom, company_id in self.COMPANIES:
            if len(offres) >= max_results:
                break
            try:
                resp = requests.get(
                    self.API_URL.format(company=company_id),
                    params={"mode": "json"},
                    timeout=10
                )
                if resp.status_code in (404, 403):
                    continue
                if resp.status_code != 200:
                    continue

                for o in resp.json():
                    titre    = o.get("text", "") or ""
                    cats     = o.get("categories", {}) or {}
                    location = cats.get("location", "") or o.get("workplaceType", "") or ""
                    team     = cats.get("team", "") or ""
                    commit   = cats.get("commitment", "") or ""

                    # Filtre : stage/alternance uniquement
                    is_stage = any(m in titre.lower() for m in self._STAGE_MOTS) \
                               or any(m in commit.lower() for m in self._STAGE_MOTS)
                    if not is_stage:
                        continue

                    # Filtre : IDF ou remote
                    if not self._is_idf_or_remote(location):
                        continue

                    # Filtre : keywords optionnels
                    if kw_list and not any(k in titre.lower() or k in team.lower() for k in kw_list):
                        continue

                    urls = o.get("urls", {}) or {}
                    url  = urls.get("show", "") or o.get("hostedUrl", "") or \
                           f"https://jobs.lever.co/{company_id}/{o.get('id', '')}"

                    offres.append({
                        "source":       "Lever",
                        "id":           o.get("id", ""),
                        "titre":        titre,
                        "entreprise":   nom,
                        "lieu":         location or "France",
                        "description":  o.get("descriptionPlain", "") or o.get("description", "") or "",
                        "date_publi":   "",
                        "url":          url,
                        "type_contrat": "Stage",
                        "salaire":      "Non précisé",
                        "duree":        "",
                    })

                time.sleep(0.3)

            except Exception:
                continue

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 8 — GREENHOUSE
#  ATS utilisé par les startups/scale-ups tech françaises : Doctolib, Criteo,
#  Contentsquare, Qonto, Dataiku, Ledger, Spendesk, Algolia, Xebia...
#  Job Board API entièrement publique — aucune clé requise.
#  Endpoint : boards-api.greenhouse.io/v1/boards/{token}/jobs
# ══════════════════════════════════════════════════════════════════════════════

class GreenhouseAPI:
    """
    Client pour la Job Board API publique de Greenhouse.
    Aucune authentification requise — données de carrière publiques.
    Le 'board_token' est l'identifiant entreprise dans l'URL Greenhouse.
    """

    API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

    # (Nom affiché, board_token Greenhouse)
    COMPANIES = [
        # Licornes & scale-ups françaises
        ("Doctolib",             "doctolib"),
        ("Contentsquare",        "contentsquare"),
        ("Ledger",               "ledger"),
        ("Criteo",               "criteo"),
        ("Spendesk",             "spendesk"),
        ("Qonto",                "qonto"),
        ("Dataiku",              "dataiku"),
        ("Mirakl",               "mirakl"),
        ("Algolia",              "algolia"),
        ("Payfit",               "payfit"),
        ("Aircall",              "aircall"),
        ("Pennylane",            "pennylane"),
        ("Pigment",              "pigment"),
        ("Xebia France",         "xebiafrance"),
        ("Comet",                "comet-1"),
        ("360Learning",          "360learning"),
        ("Leocare",              "leocare"),
        ("Nabla",                "nabla"),
        ("Sonio",                "sonio"),
        ("Stockly",              "stockly"),
        ("Alan",                 "alan"),
        ("Joko",                 "joko"),
        ("Treezor",              "treezor"),
        ("Memo Bank",            "memo-bank"),
        ("Agicap",               "agicap"),
        ("Younited",             "younited"),
        ("Shine",                "shinefr"),
        ("Lydia",                "lydia-solutions"),
        ("Alma",                 "alma"),
        ("Ankorstore",           "ankorstore"),
        ("Malt",                 "malt"),
        ("Swile",                "swile"),
        ("Brevo",                "brevo"),
        ("Skello",               "skello"),
        ("Figures",              "figures"),
        ("Spendesk",             "spendesk"),
        ("PlayPlay",             "playplay"),
        ("Lunchr",               "lunchr"),
        ("Epsor",                "epsor"),
        ("Silvr",                "silvr"),
        ("Hyperline",            "hyperline"),
        ("Defacto",              "defacto"),
        ("Deskeo",               "deskeo"),
        # Internationales présentes en France
        ("Cloudflare",           "cloudflare"),
        ("Datadog",              "datadoghq"),
        ("Elastic",              "elastic"),
        ("GitLab",               "gitlab"),
        ("Stripe",               "stripe"),
        ("Notion",               "notion"),
        ("1Password",            "1password"),
        ("Vanta",                "vanta"),
        ("Pagerduty",            "pagerduty"),
        ("Hashicorp",            "hashicorp"),
        ("Grafana Labs",         "grafanalabs"),
        ("Wiz",                  "wizsecurity"),
        ("Snyk",                 "snyk"),
        ("CrowdStrike",          "crowdstrike"),
        ("Okta",                 "okta"),
        ("Palo Alto Networks",   "paloaltonetworks"),
        ("Splunk",               "splunk"),
        ("Tenable",              "tenable"),
        ("SentinelOne",          "sentinelone"),
        ("Zscaler",              "zscaler"),
    ]

    # Mots qui indiquent un stage/alternance dans le titre
    _STAGE_MOTS = {"intern", "stage", "alternance", "apprenti", "apprentice",
                   "stagiaire", "trainee"}

    def search(self, keywords="", max_results=100):
        """
        Récupère toutes les offres de chaque entreprise et filtre :
        - Titre contenant un mot de stage/alternance
        - Localisation France / IDF / remote
        - Correspondance avec les keywords (si fournis)
        """
        offres    = []
        kw_list   = keywords.lower().split() if keywords else []

        for nom, token in self.COMPANIES:
            if len(offres) >= max_results:
                break
            try:
                resp = requests.get(
                    self.API_URL.format(token=token),
                    params={"content": "true"},
                    timeout=10
                )
                if resp.status_code in (404, 403):
                    continue
                if resp.status_code != 200:
                    continue

                for o in resp.json().get("jobs", []):
                    titre    = o.get("title", "") or ""
                    loc_name = (o.get("location", {}) or {}).get("name", "") or ""

                    # Filtre : stage / alternance uniquement
                    if not any(m in titre.lower() for m in self._STAGE_MOTS):
                        continue

                    # Filtre géographique : France / IDF / remote uniquement
                    loc_lower = loc_name.lower().strip()
                    hors_france = {
                        "london", "united kingdom", "uk", "berlin", "germany",
                        "madrid", "spain", "amsterdam", "netherlands", "dublin",
                        "ireland", "brussels", "belgium", "zurich", "switzerland",
                        "milan", "italy", "new york", "san francisco", "chicago",
                        "united states", "usa", "canada", "toronto", "singapore",
                        "sydney", "australia", "dubai",
                    }
                    if loc_name and any(ex in loc_lower for ex in hors_france):
                        continue
                    if loc_name and "france" not in loc_lower and "paris" not in loc_lower \
                            and "remote" not in loc_lower and "hybrid" not in loc_lower \
                            and "hybride" not in loc_lower and "télétravail" not in loc_lower \
                            and not any(v in loc_lower for v in ["île-de-france", "ile-de-france",
                                        "nanterre", "boulogne", "levallois", "saint-denis"]):
                        continue

                    # Filtre : keywords optionnels
                    if kw_list and not any(k in titre.lower() for k in kw_list):
                        continue

                    offres.append({
                        "source":       "Greenhouse",
                        "id":           str(o.get("id", "")),
                        "titre":        titre,
                        "entreprise":   nom,
                        "lieu":         loc_name or "France",
                        "description":  o.get("content", "") or "",
                        "date_publi":   (o.get("updated_at", "") or "")[:10],
                        "url":          o.get("absolute_url", ""),
                        "type_contrat": "Stage",
                        "salaire":      "Non précisé",
                        "duree":        "",
                    })

                time.sleep(0.3)

            except Exception:
                continue

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 7 — PASS (Place de l'Apprentissage et des Stages — Fonction Publique)
#  Site officiel : www.pass.fonction-publique.gouv.fr
#  Couvre État, Territorial, Hospitalier — sans clé, scraping HTML Drupal.
#  Paramètres URL découverts par inspection des URLs de recherche du site.
# ══════════════════════════════════════════════════════════════════════════════

class PassFonctionPubliqueAPI:
    """
    Scraper pour PASS — Place de l'Apprentissage et des Stages dans la
    Fonction Publique (pass.fonction-publique.gouv.fr).
    Site Drupal — les résultats sont dans le HTML de la page de recherche.
    Paramètres clés :
      - combine          : recherche plein texte
      - field_type_de_contrat_value[stage]=stage : filtre stage
      - field_domaine_d_activite_target_id[0]=1107 : domaine Informatique
      - field_region_target_id[0]=856 : Île-de-France
      - items_per_page   : 24 max par page
      - page             : pagination (commence à 0)
    """

    BASE_URL   = "https://www.pass.fonction-publique.gouv.fr"
    SEARCH_URL = "https://www.pass.fonction-publique.gouv.fr/recherche-offre"
    HEADERS = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
    # ID Île-de-France dans le référentiel PASS
    REGION_IDF = "856"
    # ID domaine Informatique/Numérique dans le référentiel PASS
    DOMAINE_INFORMATIQUE = "1107"

    def _parse_html(self, html):
        """
        Extrait les offres depuis le HTML Drupal de PASS.
        Les offres sont dans des blocs article ou div.views-row avec
        des liens vers /offre/{slug}.
        """
        offres = []
        # Drupal Views : découpe par bloc offre
        blocs = re.split(r'(?=<(?:article|div)[^>]+class="[^"]*views-row[^"]*")', html)

        for bloc in blocs[1:]:
            try:
                # URL de l'offre
                url_m = re.search(r'href="(/offre/[^"?]+)"', bloc)
                if not url_m:
                    continue
                url = self.BASE_URL + url_m.group(1)
                slug = url_m.group(1).split("/")[-1]

                # Titre
                titre_m = re.search(r'<h[23][^>]*>\s*<a[^>]*>(.*?)</a>', bloc, re.DOTALL)
                if not titre_m:
                    titre_m = re.search(r'<h[23][^>]*>(.*?)</h[23]>', bloc, re.DOTALL)
                titre = re.sub(r'<[^>]+>', '', titre_m.group(1)).strip() if titre_m else ""
                if not titre:
                    continue

                # Employeur / structure
                emp_m      = re.search(r'class="[^"]*(?:employeur|structure|organisation)[^"]*"[^>]*>(.*?)</(?:span|div|p)>', bloc, re.DOTALL)
                entreprise = re.sub(r'<[^>]+>', '', emp_m.group(1)).strip() if emp_m else "Fonction Publique"

                # Lieu
                lieu_m = re.search(r'class="[^"]*(?:localisation|lieu|ville|region)[^"]*"[^>]*>(.*?)</(?:span|div|p)>', bloc, re.DOTALL)
                lieu   = re.sub(r'<[^>]+>', '', lieu_m.group(1)).strip() if lieu_m else "Île-de-France"

                # Type de contrat (stage ou apprentissage)
                contrat_m    = re.search(r'class="[^"]*(?:contrat|type)[^"]*"[^>]*>(.*?)</(?:span|div|p)>', bloc, re.DOTALL)
                type_contrat = re.sub(r'<[^>]+>', '', contrat_m.group(1)).strip() if contrat_m else "Stage"
                if "apprenti" in type_contrat.lower():
                    type_contrat = "Alternance"
                else:
                    type_contrat = "Stage"

                offres.append({
                    "source":       "PASS Fonction Publique",
                    "id":           slug,
                    "titre":        titre,
                    "entreprise":   entreprise,
                    "lieu":         lieu,
                    "description":  "",
                    "date_publi":   "",
                    "url":          url,
                    "type_contrat": type_contrat,
                    "salaire":      "Non précisé",
                    "duree":        "",
                })
            except Exception:
                continue

        return offres

    def search(self, keywords="", max_results=48):
        """
        Recherche des offres de stage et d'apprentissage IT dans la
        Fonction Publique, filtrées sur l'Île-de-France.
        """
        offres = []
        page   = 0

        while len(offres) < max_results:
            try:
                # Les paramètres sont passés en query string style Drupal
                params = {
                    "field_type_de_contrat_value[stage]":        "stage",
                    "field_type_de_contrat_value[apprentissage]": "apprentissage",
                    "combine":                                    keywords,
                    "field_domaine_d_activite_target_id[0]":     self.DOMAINE_INFORMATIQUE,
                    "field_region_target_id[0]":                 self.REGION_IDF,
                    "items_per_page":                            24,
                    "page":                                      page,
                    "loadall":                                   "Rechercher toutes les offres",
                }
                resp = requests.get(self.SEARCH_URL, params=params, headers=self.HEADERS, timeout=15)
                if resp.status_code != 200 or len(resp.text) < 500:
                    break

                nouvelles = self._parse_html(resp.text)
                if not nouvelles:
                    break

                offres.extend(nouvelles)
                if len(nouvelles) < 24:
                    break
                page += 1
                time.sleep(1)

            except Exception as e:
                print(f"  ❌ PASS Fonction Publique page {page} : {e}")
                break

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 6 — STAGES ÎLE-DE-FRANCE (Open Data officiel Région IDF)
#  API Opendatasoft — gratuite, sans clé, données officielles de la Région.
#  Dataset : https://data.iledefrance.fr/explore/dataset/trouvez-un-stage/
# ══════════════════════════════════════════════════════════════════════════════

class StagesIleDeFranceAPI:
    """
    Client pour l'API Open Data officielle de la Région Île-de-France.
    Agrège les offres publiées sur stages.iledefrance.fr — sans clé requise.
    """

    API_URL = "https://data.iledefrance.fr/api/records/1.0/search/"

    def search(self, keywords, max_results=100):
        """
        Recherche des offres dans le dataset 'trouvez-un-stage'.
        L'API Opendatasoft accepte des requêtes plein texte sans authentification.
        """
        offres = []
        start  = 0
        rows   = min(100, max_results)

        while len(offres) < max_results:
            try:
                params = {
                    "dataset": "trouvez-un-stage",
                    "q":       keywords,
                    "rows":    rows,
                    "start":   start,
                    "lang":    "fr",
                }
                resp = requests.get(self.API_URL, params=params, timeout=15)
                if resp.status_code != 200:
                    break
                data    = resp.json()
                records = data.get("records", [])
                if not records:
                    break

                for rec in records:
                    f = rec.get("fields", {})

                    # Reconstruction de l'URL — le dataset fournit parfois un lien direct
                    url = f.get("lien_offre") or f.get("url") or f.get("lien") or ""
                    if not url:
                        record_id = rec.get("recordid", "")
                        url = f"https://stages.iledefrance.fr/offres/{record_id}" if record_id else "https://stages.iledefrance.fr"

                    offres.append({
                        "source":       "Stages IDF",
                        "id":           rec.get("recordid", ""),
                        "titre":        f.get("intitule_poste") or f.get("titre") or f.get("libelle_poste") or "Sans titre",
                        "entreprise":   f.get("nom_entreprise") or f.get("employeur") or f.get("raison_sociale") or "Non précisé",
                        "lieu":         f.get("ville") or f.get("commune") or f.get("lieu") or "Île-de-France",
                        "description":  f.get("description") or f.get("descriptif") or f.get("profil") or "",
                        "date_publi":   (f.get("date_publication") or f.get("date_debut") or "")[:10],
                        "url":          url,
                        "type_contrat": "Stage",
                        "salaire":      f.get("remuneration") or "Non précisé",
                        "duree":        f.get("duree") or f.get("duree_stage") or "",
                    })

                if len(records) < rows:
                    break
                start += rows
                time.sleep(0.5)

            except Exception as e:
                print(f"  ❌ Stages IDF [{keywords}] : {e}")
                break

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 6 — WELCOME TO THE JUNGLE
#  Pas d'API officielle — utilise l'API Algolia interne (clés publiques).
#  Les credentials Algolia sont extraits dynamiquement depuis le JS de la page.
#  WTTJ = référence pour les stages IT en France (Orange, Thales, Capgemini...).
# ══════════════════════════════════════════════════════════════════════════════

class WelcomeToTheJungleAPI:
    """
    Scraper pour Welcome to the Jungle via leur API Algolia interne.
    Les clés Algolia sont publiques (search-only) et embarquées dans le JS.
    """

    BASE_URL   = "https://www.welcometothejungle.com"
    SEARCH_URL = "https://www.welcometothejungle.com/fr/jobs"
    HEADERS = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Referer":         "https://www.welcometothejungle.com/fr/jobs",
    }

    def _get_algolia_creds(self):
        """Extrait l'App ID et l'API Key Algolia depuis le JS de WTTJ."""
        try:
            resp = requests.get(self.BASE_URL + "/fr", headers=self.HEADERS, timeout=15)
            if resp.status_code != 200:
                return None, None
            html = resp.text
            # Patterns pour trouver les credentials Algolia dans le bundle JS
            patterns_id = [
                r'"ALGOLIA_APP_ID"\s*:\s*"([A-Z0-9]{8,12})"',
                r'algoliaAppId["\s:]+([A-Z0-9]{8,12})',
                r'"appId"\s*:\s*"([A-Z0-9]{8,12})"',
            ]
            patterns_key = [
                r'"ALGOLIA_API_KEY"\s*:\s*"([a-f0-9]{32})"',
                r'algoliaApiKey["\s:]+([a-f0-9]{32})',
                r'"apiKey"\s*:\s*"([a-f0-9]{32})"',
            ]
            app_id = None
            api_key = None
            for p in patterns_id:
                m = re.search(p, html)
                if m:
                    app_id = m.group(1)
                    break
            for p in patterns_key:
                m = re.search(p, html)
                if m:
                    api_key = m.group(1)
                    break
            return app_id, api_key
        except Exception:
            return None, None

    def _parse_next_data(self, html, label_contrat):
        """Extrait les offres depuis le JSON __NEXT_DATA__ embarqué par Next.js."""
        offres = []
        try:
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html)
            if not m:
                return []
            data = json.loads(m.group(1))
            pp = data.get("props", {}).get("pageProps", {})

            # WTTJ change parfois la structure — on essaie plusieurs chemins
            jobs_raw = (
                pp.get("jobs", {}).get("hits", [])
                or pp.get("hits", [])
                or pp.get("data", {}).get("jobs", {}).get("hits", [])
                or pp.get("initialState", {}).get("jobs", {}).get("hits", [])
                or []
            )

            for o in jobs_raw:
                slug       = o.get("slug", "")
                company    = o.get("organization", {}) or o.get("company", {}) or {}
                comp_name  = company.get("name", "Non précisé")
                comp_slug  = company.get("slug", "")
                url = f"{self.BASE_URL}/fr/companies/{comp_slug}/jobs/{slug}" if slug and comp_slug else self.SEARCH_URL

                offres.append({
                    "source":       "Welcome to the Jungle",
                    "id":           slug or str(o.get("objectID", "")),
                    "titre":        o.get("name", "Sans titre"),
                    "entreprise":   comp_name,
                    "lieu":         o.get("city", "") or o.get("location", {}).get("city", ""),
                    "description":  o.get("description", "") or o.get("profile", ""),
                    "date_publi":   (o.get("published_at", "") or "")[:10],
                    "url":          url,
                    "type_contrat": label_contrat,
                    "salaire":      "Non précisé",
                    "duree":        o.get("contract_duration", ""),
                })
        except Exception:
            pass
        return offres

    def search(self, keywords, location="Île-de-France", max_results=25, label_contrat="Stage"):
        """
        Recherche des offres sur WTTJ.
        Essaie d'abord l'API Algolia interne, puis repli sur le parsing __NEXT_DATA__.
        """
        offres = []
        try:
            params = {
                "query":       keywords,
                "aroundQuery": "Paris, France",
                "page":        1,
            }
            if label_contrat == "Stage":
                params["contractType[]"] = "internship"
            elif label_contrat == "CDD":
                params["contractType[]"] = "fixed_term"

            resp = requests.get(
                self.SEARCH_URL,
                params=params,
                headers=self.HEADERS,
                timeout=15
            )
            if resp.status_code == 200 and len(resp.text) > 500:
                offres = self._parse_next_data(resp.text, label_contrat)

        except Exception as e:
            print(f"  ❌ Welcome to the Jungle [{keywords}] : {e}")

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 6 — STAGE.FR
#  Agrégateur dédié stage / alternance — accessible sans clé.
#  Scraping HTML des pages de résultats de recherche.
# ══════════════════════════════════════════════════════════════════════════════

class StageFrAPI:
    """
    Scraper pour Stage.fr — agrégateur de stages français.
    Pas d'API officielle — parsing HTML des résultats publics.
    """

    SEARCH_URL = "https://www.stage.fr/offres"
    HEADERS = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }

    def _parse_html(self, html):
        """Extrait les offres de stage depuis le HTML de Stage.fr."""
        offres = []
        # Stage.fr affiche des blocs article avec data-offer ou des liens /offres/{id}
        blocs = re.split(r'(?=<article|<div[^>]+class="[^"]*offer[^"]*")', html)

        for bloc in blocs[1:]:
            try:
                # URL et ID
                url_m  = re.search(r'href="(https?://(?:www\.)?stage\.fr/offres/[^"]+)"', bloc)
                if not url_m:
                    url_m = re.search(r'href="(/offres/[^"]+)"', bloc)
                url = url_m.group(1) if url_m else ""
                if url and url.startswith("/"):
                    url = "https://www.stage.fr" + url

                # Titre
                titre_m = re.search(r'<h[123][^>]*>\s*(.*?)\s*</h[123]>', bloc, re.DOTALL)
                titre = re.sub(r'\s+', ' ', titre_m.group(1)).strip() if titre_m else ""
                titre = re.sub(r'<[^>]+>', '', titre).strip()

                # Entreprise
                ent_m      = re.search(r'class="[^"]*company[^"]*"[^>]*>\s*(.*?)\s*</(?:span|p|div|a)>', bloc, re.DOTALL)
                entreprise = re.sub(r'<[^>]+>', '', ent_m.group(1)).strip() if ent_m else "Non précisé"

                # Lieu
                lieu_m = re.search(r'class="[^"]*location[^"]*"[^>]*>\s*(.*?)\s*</(?:span|p|div)>', bloc, re.DOTALL)
                lieu   = re.sub(r'<[^>]+>', '', lieu_m.group(1)).strip() if lieu_m else ""

                # Description courte
                desc_m = re.search(r'class="[^"]*description[^"]*"[^>]*>\s*(.*?)\s*</(?:p|div)>', bloc, re.DOTALL)
                desc   = re.sub(r'<[^>]+>', ' ', desc_m.group(1)).strip() if desc_m else ""
                desc   = re.sub(r'\s+', ' ', desc).strip()

                if titre and url:
                    offres.append({
                        "source":       "Stage.fr",
                        "id":           url.split("/")[-1][:30],
                        "titre":        titre,
                        "entreprise":   entreprise,
                        "lieu":         lieu,
                        "description":  desc,
                        "date_publi":   "",
                        "url":          url,
                        "type_contrat": "Stage",
                        "salaire":      "Non précisé",
                        "duree":        "",
                    })
            except Exception:
                continue

        return offres

    def search(self, keywords, location="Île-de-France", max_results=25):
        """Recherche des offres de stage sur Stage.fr."""
        offres = []
        try:
            params = {
                "keywords":    keywords,
                "localisation": location,
            }
            resp = requests.get(self.SEARCH_URL, params=params, headers=self.HEADERS, timeout=15)
            if resp.status_code == 200 and len(resp.text) > 500:
                offres = self._parse_html(resp.text)
            else:
                print(f"  ⚠️  Stage.fr [{keywords}] : réponse vide (status {resp.status_code})")
            time.sleep(1)
        except Exception as e:
            print(f"  ❌ Stage.fr [{keywords}] : {e}")

        return offres[:max_results]


# ══════════════════════════════════════════════════════════════════════════════
#  MOTEUR DE SCORING
#  Calcule un score de pertinence 0-100 pour chaque offre
# ══════════════════════════════════════════════════════════════════════════════

def scorer_offre(offre):
    """
    Calcule un score de pertinence pour une offre.
    Retourne un score entre 0 et 100, et les mots-clés trouvés.
    """
    texte = (offre["titre"] + " " + offre["description"]).lower()

    # Élimination si mot-clé négatif dans le titre OU la localisation
    titre_lower = offre["titre"].lower()
    lieu_lower  = offre.get("lieu", "").lower()
    for mot_negatif in PROFIL["mots_cles_negatifs"]:
        if mot_negatif in titre_lower or mot_negatif in lieu_lower:
            return 0, []

    score = 0
    mots_trouves = []

    # Points pour chaque compétence clé (avec poids)
    for mot, poids in PROFIL["poids"].items():
        if mot in texte:
            score += poids
            mots_trouves.append(mot)

    # Bonus pour les mots-clés positifs généraux (1 pt chacun)
    for mot in PROFIL["mots_cles_positifs"]:
        if mot not in PROFIL["poids"] and mot in texte:
            score += 1
            if mot not in mots_trouves:
                mots_trouves.append(mot)

    # Bonus si "stage" ou "alternance" dans le titre
    if any(m in titre_lower for m in ["stage", "alternance", "apprenti"]):
        score += 5

    # ── Bonus thématiques ────────────────────────────────────────────────────
    # Couvre les offres qui utilisent un vocabulaire RH généraliste plutôt que
    # des noms d'outils spécifiques (ex : "administration système" au lieu de
    # "linux", "administration réseau" au lieu de "vlan"...).
    themes = {
        "admin_sys": (
            # FR
            ["administration système", "administrateur système", "admin sys",
             "technicien système", "systèmes informatiques", "administration systèmes",
             "gestion des systèmes", "maintenance des systèmes",
             # EN
             "systems administration", "system administrator", "sysadmin",
             "it administrator", "systems engineer", "it operations"],
            8
        ),
        "admin_reseau": (
            # FR
            ["administration réseau", "administrateur réseau", "gestion réseau",
             "réseaux informatiques", "ingénieur réseau", "équipements réseau",
             "routeurs", "switches",
             # EN
             "network administration", "network administrator", "network engineer",
             "network operations", "network infrastructure", "routing", "switching"],
            8
        ),
        "infra": (
            # FR + EN
            ["infrastructure", "virtualisation", "serveurs", "datacenter", "parc informatique",
             "virtualization", "servers", "data center", "on-premise", "hybrid cloud"],
            4
        ),
        "secu_info": (
            # FR
            ["sécurité informatique", "protection des données", "politique de sécurité",
             "incidents de sécurité", "firewalls", "antivirus", "pare-feu",
             # EN
             "information security", "cybersecurity", "security operations",
             "incident response", "threat detection", "vulnerability management",
             "security analyst", "soc analyst", "penetration testing"],
            6
        ),
        "supervision2": (
            # FR + EN
            ["supervision", "monitoring", "performances réseau", "disponibilité",
             "nagios", "wireshark", "analyse des performances",
             "observability", "alerting", "uptime", "sla", "performance monitoring"],
            5
        ),
        "protocoles": (
            # FR + EN
            ["tcp/ip", "vlan", "switching", "routing", "protocoles réseau",
             "bgp", "ospf", "mpls", "network protocols", "load balancing",
             "dns management", "dhcp management"],
            4
        ),
        "support_tech": (
            # FR + EN
            ["support technique", "helpdesk", "assistance utilisateur",
             "résolution d'incidents", "tickets", "incidents techniques",
             "technical support", "it support", "help desk", "service desk",
             "troubleshooting", "l1 support", "l2 support"],
            2
        ),
        "cloud_devops": (
            # EN principalement (offres ATS en anglais)
            ["cloud infrastructure", "cloud architect", "devops engineer",
             "site reliability", "platform engineer", "infrastructure as code",
             "iac", "pipeline", "deployment", "containerization"],
            5
        ),
    }
    for _theme, (mots_theme, bonus) in themes.items():
        if any(m in texte for m in mots_theme):
            score += bonus

    # ── Normalisation réaliste ───────────────────────────────────────────────
    # Le max théorique (somme de tous les poids) dépasse 150 pts et est
    # inatteignable pour une vraie offre. On normalise sur 60 pts :
    #   • offre généraliste bien alignée  → ~40-50 pts → 65-80/100
    #   • offre très technique (cite docker + ansible + linux + AD...) → >60 pts → 100/100
    SCORE_MAX_REALISTE = 60
    score_normalise = min(100, int((score / SCORE_MAX_REALISTE) * 100))

    return score_normalise, mots_trouves


def deduplication(offres):
    """Supprime les doublons basés sur le titre + entreprise."""
    vus      = set()
    uniques  = []
    for offre in offres:
        cle = f"{offre['titre'].lower().strip()}_{offre['entreprise'].lower().strip()}"
        if cle not in vus:
            vus.add(cle)
            uniques.append(offre)
    return uniques


# ══════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATEUR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═" * 60)
    print("  🔍 STAGE HUNTER — Nabil Abboud")
    print(f"  📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("  📍 Zone : Île-de-France")
    print("  🎯 Types : Stage + CDD 4-6 mois")
    print("═" * 60)

    toutes_offres = []
    ft   = FranceTravailAPI()
    az   = AdzunaAPI()
    jb   = JoobleAPI()
    li   = LinkedInAPI()
    sr   = SmartRecruitersAPI()
    lv   = LeverAPI()
    gh   = GreenhouseAPI()
    pep  = PassFonctionPubliqueAPI()
    idf  = StagesIleDeFranceAPI()
    wttj = WelcomeToTheJungleAPI()
    sfr  = StageFrAPI()

    # ── France Travail — STAGES ───────────────────────────────
    # typeContrat=STA invalide : les stages sont des conventions, pas des contrats.
    # On force "stage" dans chaque keyword pour ne ramener que des offres de stage.
    print("\n📡 France Travail — Stages...")
    offres_ft_stages = []
    for kw in ["stage informatique", "stage linux", "stage reseau", "stage systemes"]:
        r = ft.search(keywords=kw, type_contrat=None, max_results=25)
        for o in r:
            o["type_contrat"] = "Stage"
        offres_ft_stages.extend(r)
        time.sleep(0.5)
    print(f"  ✅ {len(offres_ft_stages)} offres")
    toutes_offres.extend(offres_ft_stages)
    time.sleep(1)

    # ── France Travail — CDD ──────────────────────────────────
    # typeContrat=CDD est valide dans l'API.
    print("\n📡 France Travail — CDD...")
    offres_ft_cdd = []
    for kw in ["administrateur systemes", "admin reseau", "technicien linux"]:
        r = ft.search(keywords=kw, type_contrat="CDD", max_results=25)
        offres_ft_cdd.extend(r)
        time.sleep(0.5)
    print(f"  ✅ {len(offres_ft_cdd)} offres")
    toutes_offres.extend(offres_ft_cdd)
    time.sleep(1)

    # ── Adzuna — STAGES ───────────────────────────────────────
    # Adzuna FR ne supporte pas contract_type — recherche AND stricte (1-2 mots).
    # "stage" dans le keyword garantit des offres de stage.
    print("\n📡 Adzuna — Stages...")
    offres_az_stages = []
    for kw in ["stage informatique", "stage linux", "stage reseau"]:
        r = az.search(keywords=kw, location="Ile-de-France", max_results=25)
        for o in r:
            o["type_contrat"] = "Stage"
        offres_az_stages.extend(r)
        time.sleep(0.5)
    print(f"  ✅ {len(offres_az_stages)} offres")
    toutes_offres.extend(offres_az_stages)
    time.sleep(1)

    # ── Adzuna — CDD ──────────────────────────────────────────
    print("\n📡 Adzuna — CDD...")
    offres_az_cdd = []
    for kw in ["administrateur systemes", "windows server", "technicien linux"]:
        r = az.search(keywords=kw, location="Ile-de-France", max_results=25)
        for o in r:
            o["type_contrat"] = "CDD"
        offres_az_cdd.extend(r)
        time.sleep(0.5)
    print(f"  ✅ {len(offres_az_cdd)} offres")
    toutes_offres.extend(offres_az_cdd)
    time.sleep(1)

    # ── Jooble — STAGES ───────────────────────────────────────
    print("\n📡 Jooble — Stages (Indeed, HelloWork, APEC...)...")
    offres = jb.search(
        keywords="stage technicien administrateur systèmes linux sécurité windows active directory",
        location="Île-de-France",
        max_results=50
    )
    print(f"  ✅ {len(offres)} offres")
    toutes_offres.extend(offres)
    time.sleep(1)

    # ── Jooble — CDD ──────────────────────────────────────────
    print("\n📡 Jooble — CDD (Indeed, HelloWork, APEC...)...")
    offres = jb.search(
        keywords="CDD administrateur systèmes réseaux linux sécurité windows server",
        location="Île-de-France",
        max_results=50
    )
    print(f"  ✅ {len(offres)} offres")
    toutes_offres.extend(offres)
    time.sleep(1)

    # ── LinkedIn — STAGES ─────────────────────────────────────
    # Note : location="Ile-de-France" (sans accent, sans ", France") — requis par LinkedIn
    print("\n📡 LinkedIn — Stages...")
    offres_li_stages = []
    for kw in ["stage administrateur systemes linux", "stage reseau securite informatique"]:
        r = li.search(keywords=kw, location="Ile-de-France", max_results=20, label_contrat="Stage")
        offres_li_stages.extend(r)
    print(f"  ✅ {len(offres_li_stages)} offres")
    toutes_offres.extend(offres_li_stages)
    time.sleep(2)

    # ── LinkedIn — CDD ────────────────────────────────────────
    print("\n📡 LinkedIn — CDD...")
    offres_li_cdd = []
    for kw in ["CDD administrateur systemes linux", "technicien reseau windows server"]:
        r = li.search(keywords=kw, location="Ile-de-France", max_results=20, label_contrat="CDD")
        offres_li_cdd.extend(r)
    print(f"  ✅ {len(offres_li_cdd)} offres")
    toutes_offres.extend(offres_li_cdd)
    time.sleep(1)

    # ── SmartRecruiters — STAGES ─────────────────────────────
    print("\n📡 SmartRecruiters — Stages (Capgemini, Atos, Orange, BNP...)...")
    offres_sr = sr.search(keywords="", max_results=200, type_emploi="INTERN")
    print(f"  ✅ {len(offres_sr)} offres")
    toutes_offres.extend(offres_sr)
    time.sleep(1)

    # ── Lever — STAGES ───────────────────────────────────────
    print("\n📡 Lever — Stages (BlaBlaCar, Malt, OVHcloud, Back Market...)...")
    offres_lv = lv.search(keywords="", max_results=150)
    print(f"  ✅ {len(offres_lv)} offres")
    toutes_offres.extend(offres_lv)
    time.sleep(1)

    # ── Greenhouse — STAGES ───────────────────────────────────
    print("\n📡 Greenhouse — Stages (Doctolib, Criteo, Qonto, Xebia...)...")
    offres_gh = gh.search(keywords="", max_results=100)
    print(f"  ✅ {len(offres_gh)} offres")
    toutes_offres.extend(offres_gh)
    time.sleep(1)

    # ── PASS Fonction Publique ────────────────────────────────
    # Filtre déjà sur domaine Informatique + région IDF dans les paramètres.
    # On fait deux passes : une générale + une ciblée sécurité/réseau.
    print("\n📡 PASS Fonction Publique (stages & alternance IT)...")
    offres_pep = []
    for kw in ["", "réseau sécurité", "systèmes linux", "cybersécurité"]:
        r = pep.search(keywords=kw, max_results=48)
        offres_pep.extend(r)
        time.sleep(1)
    print(f"  ✅ {len(offres_pep)} offres")
    toutes_offres.extend(offres_pep)
    time.sleep(1)

    # ── Stages Île-de-France (Open Data officiel) ────────────
    print("\n📡 Stages IDF (Open Data Région)...")
    offres_idf = []
    for kw in ["informatique réseau", "cybersécurité", "systèmes linux", "administrateur infrastructure"]:
        r = idf.search(keywords=kw, max_results=50)
        offres_idf.extend(r)
        time.sleep(0.5)
    print(f"  ✅ {len(offres_idf)} offres")
    toutes_offres.extend(offres_idf)
    time.sleep(1)

    # ── Welcome to the Jungle — STAGES ───────────────────────
    print("\n📡 Welcome to the Jungle — Stages...")
    offres_wttj_stages = []
    for kw in ["stage systèmes réseaux", "stage cybersécurité", "stage infrastructure", "stage administrateur"]:
        r = wttj.search(keywords=kw, max_results=20, label_contrat="Stage")
        offres_wttj_stages.extend(r)
        time.sleep(1)
    print(f"  ✅ {len(offres_wttj_stages)} offres")
    toutes_offres.extend(offres_wttj_stages)
    time.sleep(1)

    # ── Welcome to the Jungle — CDD ───────────────────────────
    print("\n📡 Welcome to the Jungle — CDD...")
    offres_wttj_cdd = []
    for kw in ["administrateur systèmes réseaux", "technicien infrastructure", "ingénieur sécurité"]:
        r = wttj.search(keywords=kw, max_results=20, label_contrat="CDD")
        offres_wttj_cdd.extend(r)
        time.sleep(1)
    print(f"  ✅ {len(offres_wttj_cdd)} offres")
    toutes_offres.extend(offres_wttj_cdd)
    time.sleep(1)

    # ── Stage.fr — STAGES ─────────────────────────────────────
    print("\n📡 Stage.fr — Stages...")
    offres_sfr = []
    for kw in ["systèmes réseaux", "cybersécurité", "infrastructure informatique"]:
        r = sfr.search(keywords=kw, max_results=20)
        offres_sfr.extend(r)
        time.sleep(1)
    print(f"  ✅ {len(offres_sfr)} offres")
    toutes_offres.extend(offres_sfr)
    time.sleep(1)

    # ── Enrichissement descriptions LinkedIn ──────────────────
    # Les offres LinkedIn n'ont pas de description par défaut (scraping HTML
    # limité). On va chercher la description sur chaque page /jobs/view/.
    # max_fetch=15 pour ne pas déclencher le anti-bot LinkedIn.
    all_li = offres_li_stages + offres_li_cdd
    if all_li:
        print(f"\n🔎 Récupération des descriptions LinkedIn ({len(all_li)} offres, max 15)...")
        nb_enrichies = li.enrich_descriptions(all_li, max_fetch=15)
        print(f"  ✅ {nb_enrichies} descriptions récupérées")
    time.sleep(1)

    # ── Déduplication ─────────────────────────────────────────
    avant = len(toutes_offres)
    toutes_offres = deduplication(toutes_offres)
    print(f"\n🔄 Déduplication : {avant} → {len(toutes_offres)} offres uniques")

    # ── Scoring ───────────────────────────────────────────────
    print("\n⚡ Scoring des offres...")
    for offre in toutes_offres:
        score, mots = scorer_offre(offre)
        offre["score"]        = score
        offre["mots_trouves"] = mots

    toutes_offres.sort(key=lambda x: x["score"], reverse=True)

    # Stats
    stages = [o for o in toutes_offres if o["type_contrat"] == "Stage"]
    cdds   = [o for o in toutes_offres if o["type_contrat"] == "CDD"]
    top    = [o for o in toutes_offres if o["score"] >= 70]
    print(f"  📊 {len(stages)} stages · {len(cdds)} CDD · {len(top)} offres ≥ 70/100")
    if toutes_offres:
        print(f"  🏆 Meilleur : {toutes_offres[0]['score']}/100 — {toutes_offres[0]['titre'][:55]}")

    # ── Rapport HTML ──────────────────────────────────────────
    print("\n📝 Génération du rapport HTML...")
    output_path = generate_html_report(toutes_offres, PROFIL)
    print(f"  ✅ {output_path}")
    print("\n" + "═" * 60)
    print("  🎉 Ouvre rapport_stages.html dans ton navigateur !")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
