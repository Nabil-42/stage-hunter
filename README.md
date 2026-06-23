# 🔍 Stage Hunter

Agrégateur de recherche de **stages / alternances / CDD** qui interroge **11 sources**
en une seule commande, **score** chaque offre selon ton profil, et génère un
**rapport HTML** trié et lisible.

Configuré par défaut pour un profil **Admin Systèmes / Réseaux / Sécurité en
Île-de-France**, mais tout (mots-clés, pondération, zone) se règle en haut du
fichier `job_hunter.py`.

---

## ✨ Ce que ça fait

1. **Agrège** les offres de 11 sources (APIs officielles + ATS publics + scraping).
2. **Déduplique** (même titre + même entreprise).
3. **Score** chaque offre sur 100 selon des mots-clés pondérés (Linux, Docker,
   Active Directory, cybersécurité, réseau…) et des malus (offres hors sujet).
4. **Génère** `rapport_stages.html` : offres triées par score, badges
   *Excellent / Bon / Partiel*, filtres par source et type de contrat.

---

## 📡 Les 11 sources

**Avec clé API gratuite** (voir `.env.example`) :

| Source | Couverture |
|---|---|
| France Travail | API officielle (ex Pôle Emploi) |
| Adzuna | Agrégateur, 250 req/mois gratuit |
| Jooble | Agrégateur : Indeed, HelloWork, APEC, Monster… |

**Sans aucune clé** (endpoints publics / open data) :

| Source | Couverture |
|---|---|
| LinkedIn Jobs | Page publique (sans compte) |
| SmartRecruiters | ATS de Capgemini, Atos, Orange, BNP… |
| Lever | ATS de BlaBlaCar, Malt, OVHcloud… |
| Greenhouse | ATS de Doctolib, Criteo, Qonto, Xebia… |
| PASS Fonction Publique | Stages/alternances secteur public |
| Stages Île-de-France | Open Data officiel Région IDF |
| Welcome to the Jungle | Offres tech |
| Stage.fr | Offres de stage |

> 💡 Une clé manquante n'empêche pas le bot de tourner : la source concernée est
> simplement ignorée. Les 8 sources sans clé fonctionnent toujours.

---

## 🚀 Démarrage rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer tes clés API (toutes gratuites — voir le fichier pour les liens)
cp .env.example .env        # Windows : copy .env.example .env
#   → édite .env avec TES clés

# 3. Lancer la recherche
python job_hunter.py

# 4. Ouvrir le rapport
#   → rapport_stages.html dans ton navigateur
```

---

## 🔑 Obtenir les clés API (gratuit)

| Source | Où |
|---|---|
| France Travail | https://francetravail.io/ → application + API « Offres d'emploi v2 » |
| Adzuna | https://developer.adzuna.com/ → créer une application |
| Jooble | https://jooble.org/api/about → formulaire en bas de page |

Les liens et instructions détaillés sont aussi dans [`.env.example`](.env.example).

---

## 🎯 Adapter à ton profil

Tout est dans le dictionnaire `PROFIL` en haut de [`job_hunter.py`](job_hunter.py) :

- `mots_cles_positifs` / `mots_cles_negatifs` — ce que tu cherches / ce que tu exclus ;
- `poids` — combien chaque compétence rapporte au score ;
- `departements_idf`, `localisation`, `rayon_km` — la zone géographique.

---

## 📂 Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `job_hunter.py` | **Script principal** — 11 sources, scoring, orchestration |
| `report_generator.py` | Génère le rapport HTML à partir des offres scorées |
| `scraper_stages.py` | Variante **légère sans clé API** (scraping HTML seul) → `stages_*.json` |
| `generer_rapport.py` | Génère le HTML à partir du dernier `stages_*.json` (variante légère) |
| `.env.example` | Modèle de configuration des clés |

> Deux modes possibles : **complet** (`job_hunter.py`, recommandé) ou **léger
> sans clé** (`scraper_stages.py` → `generer_rapport.py`).

---

## ⚠️ Usage responsable

Le bot interroge des APIs publiques et des pages publiques, avec des délais entre
requêtes pour rester poli. Respecte les CGU de chaque source et n'augmente pas
les cadences de façon agressive. Outil destiné à une **recherche d'emploi
personnelle**.

## 🛠️ Stack

Python 3.9+ · `requests` · `python-dotenv` · `BeautifulSoup` · rapport HTML autonome (zéro dépendance front).

## 📜 Licence

[MIT](LICENSE) — © 2026 Nabil Abboud
