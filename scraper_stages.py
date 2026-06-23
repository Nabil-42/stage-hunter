#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  SCRAPER STAGES — Infra / Sécu / DevSecOps — France         ║
║  Lance: python3 scraper_stages.py                           ║
╚══════════════════════════════════════════════════════════════╝

Dépendances: pip install requests beautifulsoup4
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
from datetime import datetime
from urllib.parse import urljoin

# ──────────────────────────────────────────────────────────────
# MOTS-CLÉS — adapte selon ton profil
# ──────────────────────────────────────────────────────────────
KEYWORDS = [
    "stage", "stagiaire", "internship", "intern",
    "infrastructure", "infra",
    "sécurité", "securite", "security", "cybersécurité", "cybersecurite", "cyber",
    "devsecops", "devops", "sre",
    "linux", "réseau", "network", "système", "systeme", "sysadmin",
    "ansible", "terraform", "docker", "kubernetes", "k8s",
    "cloud", "aws", "azure", "gcp",
    "administrateur systeme", "admin sys",
    "soc", "pentest", "audit", "iam", "firewall",
    "proxmox", "openstack", "virtualisation",
    "zabbix", "monitoring", "supervision",
    "ldap", "active directory",
]

# ──────────────────────────────────────────────────────────────
# LISTE DES ENTREPRISES — ~200 cibles
# Supprimé : banque, assurance, armement
# ──────────────────────────────────────────────────────────────
COMPANIES = [

    # ════════════════════════════════════════════════════════════
    # CAC 40 / GRANDS GROUPES (hors banque/assurance/armement)
    # ════════════════════════════════════════════════════════════
    {"nom": "Air Liquide",         "url": "https://careers.airliquide.com/search/?q=stage&country=France",                    "type": "custom"},
    {"nom": "Airbus",              "url": "https://www.airbus.com/en/careers/search-and-apply?search=stage&country=france",   "type": "custom"},
    {"nom": "Bouygues",            "url": "https://www.bouygues.com/groupe/rejoindre-bouygues/offres-emploi",                 "type": "custom"},
    {"nom": "Capgemini",           "url": "https://www.capgemini.com/fr-fr/carrieres/offres-d-emploi/?search=stage",          "type": "custom"},
    {"nom": "Carrefour",           "url": "https://recrutement.carrefour.com/offres?type=stage",                              "type": "custom"},
    {"nom": "Danone",              "url": "https://careers.danone.com/fr/france/search.html?type=internship",                 "type": "custom"},
    {"nom": "EDF",                 "url": "https://recrutement.edf.com/fr/offres-d-emploi#filters=STAG",                     "type": "custom"},
    {"nom": "Engie",               "url": "https://recrutement.engie.com/fr/offres-emploi/?type=stage",                      "type": "custom"},
    {"nom": "L'Oréal",             "url": "https://careers.loreal.com/fr_FR/jobs/SearchJobs/stage",                          "type": "custom"},
    {"nom": "Legrand",             "url": "https://www.legrand.com/FR/offres-emploi_2295.html",                              "type": "custom"},
    {"nom": "Michelin",            "url": "https://jobs.michelin.com/fr/offres?type=stage",                                  "type": "custom"},
    {"nom": "Orange",              "url": "https://orange.jobs/jobs/search/?lang=fr&type=internship",                        "type": "custom"},
    {"nom": "Publicis",            "url": "https://careers.publicisgroupe.com/offres?type=stage",                            "type": "custom"},
    {"nom": "Renault",             "url": "https://recrutement.renaultgroup.com/offres?type=stage",                          "type": "custom"},
    {"nom": "Saint-Gobain",        "url": "https://www.saint-gobain.com/fr/carrieres/offres-emploi?type=stage",              "type": "custom"},
    {"nom": "Schneider Electric",  "url": "https://www.se.com/ww/en/about-us/careers/search-results/?country=France&type=Internship", "type": "custom"},
    {"nom": "Stellantis",          "url": "https://www.stellantis.com/fr/carrieres/offres-emploi?type=stage",                "type": "custom"},
    {"nom": "STMicroelectronics",  "url": "https://www.st.com/content/st_com/en/about/careers/careers.html",                 "type": "custom"},
    {"nom": "Teleperformance",     "url": "https://jobs.teleperformance.com/fr/offres?type=stage",                           "type": "custom"},
    {"nom": "TotalEnergies",       "url": "https://recrutement.totalenergies.com/offres?type=stage",                         "type": "custom"},
    {"nom": "Veolia",              "url": "https://recrutement.veolia.com/fr/offres/?type=stage",                            "type": "custom"},
    {"nom": "Vinci",               "url": "https://recrutement.vinci.com/offres?type=stage",                                 "type": "custom"},
    {"nom": "Vivendi",             "url": "https://recrutement.vivendi.com/offres?type=stage",                               "type": "custom"},
    {"nom": "Worldline",           "url": "https://careers.worldline.com/fr/offres?type=stage",                              "type": "custom"},
    {"nom": "Sanofi",              "url": "https://jobs.sanofi.com/fr/search-jobs?type=internship&country=france",           "type": "custom"},
    {"nom": "Dassault Systèmes",   "url": "https://www.3ds.com/fr/carrieres/recherche-d-emploi",                            "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # ESN / CONSEIL IT / AUDIT TECH
    # ════════════════════════════════════════════════════════════
    {"nom": "Accenture",           "url": "https://www.accenture.com/fr-fr/careers/jobsearch?jk=stage",                     "type": "custom"},
    {"nom": "Alten",               "url": "https://www.alten.fr/offres-emploi/?type=stage",                                 "type": "custom"},
    {"nom": "Altran (Capgemini Eng)","url": "https://www.capgemini.com/fr-fr/carrieres/offres-d-emploi/?search=stage+ingenieur", "type": "custom"},
    {"nom": "Atos / Eviden",       "url": "https://atos.net/fr/carrieres/offres-d-emploi?type=stage",                       "type": "custom"},
    {"nom": "Aubay",               "url": "https://www.aubay.com/fr/offres-emploi/?type=stage",                             "type": "custom"},
    {"nom": "Axians",              "url": "https://www.axians.fr/carrieres/nos-offres/?type=stage",                         "type": "custom"},
    {"nom": "Beijaflore",          "url": "https://www.beijaflore.com/fr/rejoignez-nous/offres/",                           "type": "custom"},
    {"nom": "CGI France",          "url": "https://www.cgi.com/france/fr-fr/article/offres-emploi?type=intern",             "type": "custom"},
    {"nom": "Claranet",            "url": "https://www.claranet.fr/carrieres/offres-emploi",                                "type": "custom"},
    {"nom": "Computacenter",       "url": "https://www.computacenter.com/fr/carrieres/offres",                              "type": "custom"},
    {"nom": "Deloitte",            "url": "https://jobsearch.deloitte.com/search/?q=stage&location=France",                 "type": "custom"},
    {"nom": "Devoteam",            "url": "https://fr.devoteam.com/rejoindre-devoteam/nos-offres/?type=stage",              "type": "custom"},
    {"nom": "EY France (tech)",    "url": "https://careers.ey.com/ey/search/?q=stage+tech&location=france",                "type": "custom"},
    {"nom": "GFI / Inetum",        "url": "https://www.inetum.com/fr/nous-rejoindre/offres?type=stage",                    "type": "custom"},
    {"nom": "Hardis Group",        "url": "https://www.hardis-group.com/rejoignez-nous/offres-emploi",                     "type": "custom"},
    {"nom": "HCL Technologies FR", "url": "https://www.hcltech.com/careers/search-jobs?country=france",                    "type": "custom"},
    {"nom": "IBM France",          "url": "https://www.ibm.com/fr-fr/employment/",                                          "type": "custom"},
    {"nom": "Indra France",        "url": "https://www.indra.es/en/careers/job-offers?country=france",                     "type": "custom"},
    {"nom": "Infosys France",      "url": "https://www.infosys.com/careers/search-jobs.html?country=france",               "type": "custom"},
    {"nom": "Keyrus",              "url": "https://www.keyrus.com/fr-fr/rejoignez-nous/offres-emploi",                     "type": "custom"},
    {"nom": "Logicalis",           "url": "https://www.logicalis.com/fr/carrieres/",                                        "type": "custom"},
    {"nom": "Micropole",           "url": "https://www.micropole.com/fr/recrutement/nos-offres/",                          "type": "custom"},
    {"nom": "NTT Data France",     "url": "https://fr.nttdata.com/carrieres/offres-emploi",                                "type": "custom"},
    {"nom": "Neurones IT",         "url": "https://www.neurones.net/recrutement/offres-emploi/",                           "type": "custom"},
    {"nom": "Onepoint",            "url": "https://www.groupeonepoint.com/fr/nous-rejoindre/offres-emploi/",               "type": "custom"},
    {"nom": "PwC France (tech)",   "url": "https://www.pwc.fr/fr/carrieres/offres-emploi.html",                            "type": "custom"},
    {"nom": "Sia Partners",        "url": "https://www.sia-partners.com/fr/carrieres/offres-emploi",                       "type": "custom"},
    {"nom": "Sogeti (Capgemini)",  "url": "https://www.sogeti.com/fr/carrieres/offres-emploi/?type=stage",                 "type": "custom"},
    {"nom": "Sopra Steria",        "url": "https://careers.soprasteria.com/fr/offres?type=stage",                          "type": "custom"},
    {"nom": "Assystem",            "url": "https://careers.assystem.com/offres?type=stage",                                "type": "custom"},
    {"nom": "Expleo",              "url": "https://www.expleogroup.com/fr/carrieres/offres-emploi/?type=stage",            "type": "custom"},
    {"nom": "Tata Consultancy FR", "url": "https://www.tcs.com/careers/search-jobs?country=france",                        "type": "custom"},
    {"nom": "Wipro France",        "url": "https://careers.wipro.com/careers-home/jobs?country=france",                    "type": "custom"},
    {"nom": "Econocom",            "url": "https://www.econocom.com/fr/nous-rejoindre/offres-emploi",                      "type": "custom"},
    {"nom": "Avanade France",      "url": "https://www.avanade.com/fr-fr/career/job-listings",                             "type": "custom"},
    {"nom": "Modis (Akkodis)",     "url": "https://www.akkodis.com/fr/carrieres/offres-emploi",                            "type": "custom"},
    {"nom": "Scalian",             "url": "https://www.scalian.com/carrieres/offres-emploi/",                              "type": "custom"},
    {"nom": "Talan",               "url": "https://www.talan.com/fr/offres-emploi/",                                       "type": "custom"},
    {"nom": "Amiltone",            "url": "https://www.amiltone.com/recrutement/offres/",                                  "type": "custom"},
    {"nom": "Infeeny (Econocom)",  "url": "https://www.econocom.com/fr/nous-rejoindre/offres-emploi",                      "type": "custom"},
    {"nom": "Efor Group",          "url": "https://www.efor.fr/recrutement/offres-emploi/",                               "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # CYBER / SÉCURITÉ (pure players)
    # ════════════════════════════════════════════════════════════
    {"nom": "ANSSI",               "url": "https://www.ssi.gouv.fr/agence/recrutement/nos-offres/",                          "type": "custom"},
    {"nom": "Orange Cyberdefense", "url": "https://www.orangecyberdefense.com/fr/carrieres/nos-offres",                    "type": "custom"},
    {"nom": "Wavestone",           "url": "https://www.wavestone.com/fr/rejoindre/nos-offres/?type=stage",                 "type": "custom"},
    {"nom": "Synetis",             "url": "https://www.synetis.com/recrutement/",                                           "type": "custom"},
    {"nom": "Tehtris",             "url": "https://tehtris.com/fr/carrieres/",                                              "type": "custom"},
    {"nom": "Sekoia",              "url": "https://www.welcometothejungle.com/fr/companies/sekoia/jobs",                   "type": "wttj"},
    {"nom": "Stormshield",         "url": "https://www.stormshield.com/fr/carrieres/",                                     "type": "custom"},
    {"nom": "Pradeo",              "url": "https://www.pradeo.com/fr/recrutement",                                         "type": "custom"},
    {"nom": "Vade (Hornetsecurity)","url": "https://www.hornetsecurity.com/fr/carrieres/",                                 "type": "custom"},
    {"nom": "Dashlane",            "url": "https://www.dashlane.com/fr/careers",                                           "type": "custom"},
    {"nom": "Gatewatcher",         "url": "https://www.gatewatcher.com/societe/recrutement/",                              "type": "custom"},
    {"nom": "ITrust",              "url": "https://www.itrust.fr/recrutement/",                                            "type": "custom"},
    {"nom": "Yogosha",             "url": "https://www.welcometothejungle.com/fr/companies/yogosha/jobs",                  "type": "wttj"},
    {"nom": "Hackuity",            "url": "https://www.welcometothejungle.com/fr/companies/hackuity/jobs",                 "type": "wttj"},
    {"nom": "Filigran",            "url": "https://www.welcometothejungle.com/fr/companies/filigran/jobs",                 "type": "wttj"},
    {"nom": "Speeria",             "url": "https://speeria.io/recrutement",                                                "type": "custom"},
    {"nom": "Olfeo",               "url": "https://www.olfeo.com/fr/recrutement",                                          "type": "custom"},
    {"nom": "Riot (cyber)",        "url": "https://www.welcometothejungle.com/fr/companies/riot/jobs",                     "type": "wttj"},
    {"nom": "Tenacy",              "url": "https://www.welcometothejungle.com/fr/companies/tenacy/jobs",                   "type": "wttj"},
    {"nom": "Exabeam France",      "url": "https://www.exabeam.com/company/careers/",                                     "type": "custom"},
    {"nom": "Alsid (Tenable)",     "url": "https://www.tenable.com/careers",                                              "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # CLOUD / INFRA / HÉBERGEMENT / TÉLÉCOM
    # ════════════════════════════════════════════════════════════
    {"nom": "OVHcloud",            "url": "https://www.welcometothejungle.com/fr/companies/ovhcloud/jobs",                 "type": "wttj"},
    {"nom": "Scaleway",            "url": "https://www.welcometothejungle.com/fr/companies/scaleway/jobs",                 "type": "wttj"},
    {"nom": "Outscale (3DS)",      "url": "https://www.welcometothejungle.com/fr/companies/3ds-outscale/jobs",             "type": "wttj"},
    {"nom": "Ikoula",              "url": "https://www.ikoula.com/fr/recrutement",                                         "type": "custom"},
    {"nom": "Infomaniak",          "url": "https://www.infomaniak.com/fr/infomaniak/emplois",                               "type": "custom"},
    {"nom": "Colt Technology",     "url": "https://careers.colt.net/search/?q=stage&country=france",                       "type": "custom"},
    {"nom": "SFR",                 "url": "https://recrutement.sfr.fr/offres?type=stage",                                  "type": "custom"},
    {"nom": "Bouygues Telecom",    "url": "https://recrutement.bouyguestelecom.fr/offres?type=stage",                      "type": "custom"},
    {"nom": "Free / Iliad",        "url": "https://recrutement.free.fr/offres?type=stage",                                 "type": "custom"},
    {"nom": "Orange Business",     "url": "https://www.orange-business.com/fr/carrieres",                                  "type": "custom"},
    {"nom": "Celeste",             "url": "https://www.celeste.fr/recrutement/",                                           "type": "custom"},
    {"nom": "Gcore",               "url": "https://gcore.com/careers",                                                    "type": "custom"},
    {"nom": "Jaguar Network",      "url": "https://www.jaguar-network.com/recrutement/",                                   "type": "custom"},
    {"nom": "Netalis",             "url": "https://www.netalis.fr/recrutement/",                                           "type": "custom"},
    {"nom": "Numerix",             "url": "https://www.numerix.fr/recrutement/",                                           "type": "custom"},
    {"nom": "SII Group",           "url": "https://www.groupe-sii.com/fr/rejoignez-nous/offres-emploi/",                   "type": "custom"},
    {"nom": "Alphalink",           "url": "https://www.alphalink.fr/recrutement/",                                         "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # ÉNERGIE / INDUSTRIE / TRANSPORT (DSI importantes)
    # ════════════════════════════════════════════════════════════
    {"nom": "CEA",                 "url": "https://www.cea.fr/recrutement/Pages/offres-emplois-stages.aspx",               "type": "custom"},
    {"nom": "Air France",          "url": "https://careers.airfranceklm.com/search/?q=stage&locationsearch=france",        "type": "custom"},
    {"nom": "Alstom",              "url": "https://www.alstom.com/fr/carrieres/search-jobs?type=intern&country=france",   "type": "custom"},
    {"nom": "Arkema",              "url": "https://www.arkema.com/fr/carrieres/offres-emploi/",                            "type": "custom"},
    {"nom": "Eiffage",             "url": "https://recrutement.eiffage.com/offres?type=stage",                             "type": "custom"},
    {"nom": "GRT Gaz",             "url": "https://recrutement.grtgaz.com/offres?type=stage",                              "type": "custom"},
    {"nom": "La Poste",            "url": "https://legroupe.laposte.fr/offres-d-emploi?type=stage",                       "type": "custom"},
    {"nom": "RTE",                 "url": "https://recrutement.rte-france.com/offres?type=stage",                          "type": "custom"},
    {"nom": "SNCF",                "url": "https://www.emploi.sncf.com/fr/offres/recherche?type=STAGE",                   "type": "custom"},
    {"nom": "Transdev",            "url": "https://www.transdev.com/fr/carrieres/offres-emploi/?type=stage",              "type": "custom"},
    {"nom": "Suez",                "url": "https://www.suez.com/fr/rejoignez-nous/offres-emploi?type=stage",              "type": "custom"},
    {"nom": "Framatome",           "url": "https://www.framatome.com/FR/careers-604/list-of-job-offers.html",             "type": "custom"},
    {"nom": "Plastic Omnium",      "url": "https://www.plasticomnium.com/fr/carrieres/offres-emploi",                     "type": "custom"},
    {"nom": "Vallourec",           "url": "https://www.vallourec.com/fr/carrieres/offres-emploi",                         "type": "custom"},
    {"nom": "Getlink (Eurotunnel)","url": "https://www.getlinkgroup.com/fr/carrieres/offres-emploi/",                     "type": "custom"},
    {"nom": "Keolis",              "url": "https://www.keolis.com/fr/carrieres/offres-emploi",                            "type": "custom"},
    {"nom": "Lacroix Group",       "url": "https://www.lacroix-group.com/fr/rejoindre/offres/",                           "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # SECTEUR PUBLIC / RECHERCHE / ÉDUCATION
    # ════════════════════════════════════════════════════════════
    {"nom": "CNES",                "url": "https://cnes.fr/fr/recrutement",                                                "type": "custom"},
    {"nom": "INRIA",               "url": "https://jobs.inria.fr/public/classic/fr/offres",                               "type": "custom"},
    {"nom": "CNRS",                "url": "https://emploi.cnrs.fr/Offres.aspx",                                           "type": "custom"},
    {"nom": "ONERA",               "url": "https://www.onera.fr/fr/recrutement",                                          "type": "custom"},
    {"nom": "ESA (spatial)",       "url": "https://jobs.esa.int/fobx?fnc=user&page=1&type=PN",                            "type": "custom"},
    {"nom": "EPITA",               "url": "https://www.epita.fr/actualites/offres-emploi/",                               "type": "custom"},
    {"nom": "ANSM",                "url": "https://www.ansm.sante.fr/Nous-connaitre/Nous-rejoindre/Offres-d-emploi",      "type": "custom"},
    {"nom": "Inrae",               "url": "https://jobs.inrae.fr/offres",                                                 "type": "custom"},
    {"nom": "Météo France",        "url": "https://www.meteofrance.fr/nous-rejoindre/offres-d-emploi",                   "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # STARTUPS / SCALE-UPS TECH — Greenhouse
    # ════════════════════════════════════════════════════════════
    {"nom": "Contentsquare",       "url": "https://boards.greenhouse.io/contentsquare",                                    "type": "greenhouse"},
    {"nom": "Datadog",             "url": "https://boards.greenhouse.io/datadog",                                          "type": "greenhouse"},
    {"nom": "Doctolib",            "url": "https://boards.greenhouse.io/doctolib",                                         "type": "greenhouse"},
    {"nom": "Ledger",              "url": "https://boards.greenhouse.io/ledger",                                           "type": "greenhouse"},
    {"nom": "Mirakl",              "url": "https://boards.greenhouse.io/mirakl",                                           "type": "greenhouse"},
    {"nom": "Jellysmack",          "url": "https://boards.greenhouse.io/jellysmack",                                       "type": "greenhouse"},
    {"nom": "Sendinblue / Brevo",  "url": "https://boards.greenhouse.io/sendinblue",                                       "type": "greenhouse"},
    {"nom": "Meero",               "url": "https://boards.greenhouse.io/meero",                                            "type": "greenhouse"},
    {"nom": "Aircall",             "url": "https://boards.greenhouse.io/aircall",                                          "type": "greenhouse"},
    {"nom": "Lydia",               "url": "https://boards.greenhouse.io/lydia",                                            "type": "greenhouse"},

    # ════════════════════════════════════════════════════════════
    # STARTUPS / SCALE-UPS TECH — Lever
    # ════════════════════════════════════════════════════════════
    {"nom": "Alan",                "url": "https://jobs.lever.co/alan",                                                    "type": "lever"},
    {"nom": "Back Market",         "url": "https://jobs.lever.co/backmarket",                                              "type": "lever"},
    {"nom": "Payfit",              "url": "https://jobs.lever.co/payfit",                                                  "type": "lever"},
    {"nom": "Pennylane",           "url": "https://jobs.lever.co/pennylane",                                               "type": "lever"},
    {"nom": "Qonto",               "url": "https://jobs.lever.co/qonto",                                                   "type": "lever"},
    {"nom": "Spendesk",            "url": "https://jobs.lever.co/spendesk",                                                "type": "lever"},
    {"nom": "Swile",               "url": "https://jobs.lever.co/swile",                                                   "type": "lever"},
    {"nom": "Alma",                "url": "https://jobs.lever.co/alma",                                                    "type": "lever"},
    {"nom": "Pigment",             "url": "https://jobs.lever.co/pigment",                                                 "type": "lever"},
    {"nom": "Ankorstore",          "url": "https://jobs.lever.co/ankorstore",                                              "type": "lever"},
    {"nom": "Luko",                "url": "https://jobs.lever.co/luko",                                                    "type": "lever"},
    {"nom": "Epsor",               "url": "https://jobs.lever.co/epsor",                                                   "type": "lever"},
    {"nom": "Agicap",              "url": "https://jobs.lever.co/agicap",                                                  "type": "lever"},
    {"nom": "Indy",                "url": "https://jobs.lever.co/indy",                                                    "type": "lever"},

    # ════════════════════════════════════════════════════════════
    # STARTUPS / SCALE-UPS TECH — Welcome to the Jungle
    # ════════════════════════════════════════════════════════════
    {"nom": "Akeneo",              "url": "https://www.welcometothejungle.com/fr/companies/akeneo/jobs",                   "type": "wttj"},
    {"nom": "Yousign",             "url": "https://www.welcometothejungle.com/fr/companies/yousign/jobs",                  "type": "wttj"},
    {"nom": "Talend",              "url": "https://www.welcometothejungle.com/fr/companies/talend/jobs",                   "type": "wttj"},
    {"nom": "Boost.ai",            "url": "https://www.welcometothejungle.com/fr/companies/boost-ai/jobs",                "type": "wttj"},
    {"nom": "Leocare",             "url": "https://www.welcometothejungle.com/fr/companies/leocare/jobs",                 "type": "wttj"},
    {"nom": "Spendesk WTTJ",       "url": "https://www.welcometothejungle.com/fr/companies/spendesk/jobs",                "type": "wttj"},
    {"nom": "Doctrine",            "url": "https://www.welcometothejungle.com/fr/companies/doctrine/jobs",                "type": "wttj"},
    {"nom": "Padok",               "url": "https://www.welcometothejungle.com/fr/companies/padok/jobs",                   "type": "wttj"},
    {"nom": "Theodo",              "url": "https://www.welcometothejungle.com/fr/companies/theodo/jobs",                  "type": "wttj"},
    {"nom": "Bedrock Streaming",   "url": "https://www.welcometothejungle.com/fr/companies/bedrock-streaming/jobs",       "type": "wttj"},
    {"nom": "Platform.sh",         "url": "https://www.welcometothejungle.com/fr/companies/platform-sh/jobs",            "type": "wttj"},
    {"nom": "Wooclap",             "url": "https://www.welcometothejungle.com/fr/companies/wooclap/jobs",                 "type": "wttj"},
    {"nom": "Livestorm",           "url": "https://www.welcometothejungle.com/fr/companies/livestorm/jobs",               "type": "wttj"},
    {"nom": "Saagie",              "url": "https://www.welcometothejungle.com/fr/companies/saagie/jobs",                  "type": "wttj"},
    {"nom": "CleverCloud",         "url": "https://www.welcometothejungle.com/fr/companies/clever-cloud/jobs",            "type": "wttj"},
    {"nom": "Maif (DSI)",          "url": "https://www.welcometothejungle.com/fr/companies/maif/jobs",                    "type": "wttj"},
    {"nom": "Malt",                "url": "https://www.welcometothejungle.com/fr/companies/malt/jobs",                   "type": "wttj"},
    {"nom": "Wimi",                "url": "https://www.welcometothejungle.com/fr/companies/wimi/jobs",                    "type": "wttj"},
    {"nom": "Salto",               "url": "https://www.welcometothejungle.com/fr/companies/salto/jobs",                  "type": "wttj"},
    {"nom": "Lunchr / Swile",      "url": "https://www.welcometothejungle.com/fr/companies/swile/jobs",                  "type": "wttj"},
    {"nom": "Iziwork",             "url": "https://www.welcometothejungle.com/fr/companies/iziwork/jobs",                "type": "wttj"},
    {"nom": "Synapse Medicine",    "url": "https://www.welcometothejungle.com/fr/companies/synapse-medicine/jobs",        "type": "wttj"},
    {"nom": "Whisperer",           "url": "https://www.welcometothejungle.com/fr/companies/whisperer/jobs",              "type": "wttj"},
    {"nom": "Meritis",             "url": "https://www.welcometothejungle.com/fr/companies/meritis/jobs",                "type": "wttj"},

    # ════════════════════════════════════════════════════════════
    # MÉDIAS / AUDIOVISUEL / PLATEFORMES (grosses DSI)
    # ════════════════════════════════════════════════════════════
    {"nom": "TF1 Group",           "url": "https://recrutement.tf1.fr/offres?type=stage",                                 "type": "custom"},
    {"nom": "France Télévisions",  "url": "https://www.francetvpub.fr/recrutement/",                                     "type": "custom"},
    {"nom": "M6 Group",            "url": "https://recrutement.m6.fr/offres?type=stage",                                  "type": "custom"},
    {"nom": "Radio France",        "url": "https://www.radiofrance.fr/nous-rejoindre/offres-d-emploi",                   "type": "custom"},
    {"nom": "Canal+",              "url": "https://www.canalplus.com/fr/carriere/offres-d-emploi/",                       "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # RETAIL / E-COMMERCE (DSI et infra)
    # ════════════════════════════════════════════════════════════
    {"nom": "Cdiscount",           "url": "https://recrutement.cdiscount.com/offres?type=stage",                          "type": "custom"},
    {"nom": "Fnac Darty",          "url": "https://recrutement.fnacdarty.com/offres?type=stage",                          "type": "custom"},
    {"nom": "Leroy Merlin",        "url": "https://recrutement.leroymerlin.fr/offres?type=stage",                         "type": "custom"},
    {"nom": "Decathlon",           "url": "https://www.decathlon.fr/landing/recrutement/_/R-a-recrutement",              "type": "custom"},
    {"nom": "Showroomprive",       "url": "https://www.welcometothejungle.com/fr/companies/showroomprive/jobs",           "type": "wttj"},
    {"nom": "Vinted France",       "url": "https://www.welcometothejungle.com/fr/companies/vinted/jobs",                 "type": "wttj"},
    {"nom": "Leboncoin (Adevinta)","url": "https://www.welcometothejungle.com/fr/companies/leboncoin/jobs",              "type": "wttj"},
    {"nom": "ManoMano",            "url": "https://www.welcometothejungle.com/fr/companies/manomano/jobs",               "type": "wttj"},
    {"nom": "La Redoute",          "url": "https://recrutement.laredoute.fr/offres?type=stage",                           "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # SANTÉ / BIOTECH / MEDTECH (DSI)
    # ════════════════════════════════════════════════════════════
    {"nom": "Philips France",      "url": "https://www.jobs.philips.com/search/?q=stage&country=france",                 "type": "custom"},
    {"nom": "Siemens Healthineers","url": "https://www.siemens-healthineers.com/fr/careers",                             "type": "custom"},
    {"nom": "Lifen",               "url": "https://www.welcometothejungle.com/fr/companies/lifen/jobs",                  "type": "wttj"},
    {"nom": "Incepto Medical",     "url": "https://www.welcometothejungle.com/fr/companies/incepto-medical/jobs",        "type": "wttj"},
    {"nom": "Gleamer",             "url": "https://www.welcometothejungle.com/fr/companies/gleamer/jobs",                "type": "wttj"},
    {"nom": "Voluntis",            "url": "https://www.welcometothejungle.com/fr/companies/voluntis/jobs",               "type": "wttj"},

    # ════════════════════════════════════════════════════════════
    # LOGISTIQUE / SUPPLY CHAIN (DSI)
    # ════════════════════════════════════════════════════════════
    {"nom": "Geodis",              "url": "https://www.geodis.com/fr/fr/carrieres/offres-d-emploi",                      "type": "custom"},
    {"nom": "DB Schenker France",  "url": "https://www.dbschenker.com/fr-fr/carrieres",                                  "type": "custom"},
    {"nom": "Bolloré Logistics",   "url": "https://www.bollore-logistics.com/fr/carrieres/nos-offres/",                  "type": "custom"},
    {"nom": "FM Logistic",         "url": "https://www.fmlogistic.com/fr/carrieres/offres-emploi/",                     "type": "custom"},
    {"nom": "Generix Group",       "url": "https://www.welcometothejungle.com/fr/companies/generix-group/jobs",          "type": "wttj"},

    # ════════════════════════════════════════════════════════════
    # IMMOBILIER / CONSTRUCTION (DSI)
    # ════════════════════════════════════════════════════════════
    {"nom": "Bouygues Immobilier", "url": "https://recrutement.bouygues-immobilier.fr/offres?type=stage",               "type": "custom"},
    {"nom": "Nexity",              "url": "https://recrutement.nexity.fr/offres?type=stage",                             "type": "custom"},
    {"nom": "Unibail-Rodamco",     "url": "https://careers.urw.com/search/?q=stage&country=france",                     "type": "custom"},
    {"nom": "Icade",               "url": "https://recrutement.icade.fr/offres?type=stage",                              "type": "custom"},

    # ════════════════════════════════════════════════════════════
    # AUTRES STRUCTURES TECH / SPÉCIALISÉES
    # ════════════════════════════════════════════════════════════
    {"nom": "Murex",               "url": "https://www.murex.com/fr/carrieres/offres-emploi/",                           "type": "custom"},
    {"nom": "Criteo",              "url": "https://www.criteo.com/careers/",                                             "type": "custom"},
    {"nom": "Dailymotion",         "url": "https://www.welcometothejungle.com/fr/companies/dailymotion/jobs",            "type": "wttj"},
    {"nom": "Deezer",              "url": "https://www.welcometothejungle.com/fr/companies/deezer/jobs",                 "type": "wttj"},
    {"nom": "Blablacar",           "url": "https://www.welcometothejungle.com/fr/companies/blablacar/jobs",              "type": "wttj"},
    {"nom": "Vestiaire Collective","url": "https://www.welcometothejungle.com/fr/companies/vestiaire-collective/jobs",   "type": "wttj"},
    {"nom": "Meetic / Match Group","url": "https://www.welcometothejungle.com/fr/companies/meetic/jobs",                "type": "wttj"},
    {"nom": "Ogury",               "url": "https://www.welcometothejungle.com/fr/companies/ogury/jobs",                  "type": "wttj"},
    {"nom": "Teads",               "url": "https://www.welcometothejungle.com/fr/companies/teads/jobs",                  "type": "wttj"},
    {"nom": "Indy (compta)",       "url": "https://www.welcometothejungle.com/fr/companies/indy/jobs",                  "type": "wttj"},
    {"nom": "Lifen Health",        "url": "https://www.welcometothejungle.com/fr/companies/lifen/jobs",                  "type": "wttj"},
    {"nom": "360Learning",         "url": "https://www.welcometothejungle.com/fr/companies/360learning/jobs",            "type": "wttj"},
    {"nom": "Schoolmouv",          "url": "https://www.welcometothejungle.com/fr/companies/schoolmouv/jobs",            "type": "wttj"},
    {"nom": "JobTeaser",           "url": "https://www.welcometothejungle.com/fr/companies/jobteaser/jobs",             "type": "wttj"},
    {"nom": "Pennylane WTTJ",      "url": "https://www.welcometothejungle.com/fr/companies/pennylane/jobs",             "type": "wttj"},
    {"nom": "Shine",               "url": "https://www.welcometothejungle.com/fr/companies/shine/jobs",                 "type": "wttj"},
    {"nom": "Deblock",             "url": "https://www.welcometothejungle.com/fr/companies/deblock/jobs",               "type": "wttj"},
    {"nom": "Wttj (lui-même)",     "url": "https://www.welcometothejungle.com/fr/companies/welcome-to-the-jungle/jobs", "type": "wttj"},
    {"nom": "Qare",                "url": "https://www.welcometothejungle.com/fr/companies/qare/jobs",                  "type": "wttj"},
    {"nom": "Nabla",               "url": "https://www.welcometothejungle.com/fr/companies/nabla/jobs",                 "type": "wttj"},

    # ────────────────────────────────────────────────────────────
    # ⬇️  AJOUTE TES BOÎTES NICHE ICI ⬇️
    # {"nom": "Ma boite", "url": "https://maboite.fr/carrieres", "type": "custom"},
    # ────────────────────────────────────────────────────────────
]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ──────────────────────────────────────────────────────────────
# FONCTIONS DE SCRAPING
# ──────────────────────────────────────────────────────────────

def keyword_match(text: str) -> list:
    t = text.lower()
    return [kw for kw in KEYWORDS if kw.lower() in t]


def scrape_greenhouse(company: dict) -> list:
    results = []
    try:
        r = requests.get(company["url"], headers=HEADERS, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for job in soup.select(".opening"):
            a = job.select_one("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if href.startswith("/"):
                href = "https://boards.greenhouse.io" + href
            loc_el = job.select_one(".location")
            location = loc_el.get_text(strip=True) if loc_el else ""
            matched = keyword_match(title + " " + location)
            if matched:
                results.append({"entreprise": company["nom"], "poste": title,
                                 "lieu": location, "lien": href,
                                 "mots_clés": ", ".join(matched[:4]), "source": "Greenhouse"})
    except Exception as e:
        print(f"    ⚠️  {e}")
    return results


def scrape_lever(company: dict) -> list:
    results = []
    try:
        slug = company["url"].split("jobs.lever.co/")[1].strip("/")
        api = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        r = requests.get(api, headers={**HEADERS, "Accept": "application/json"}, timeout=12)
        r.raise_for_status()
        for job in r.json():
            title = job.get("text", "")
            link = job.get("hostedUrl", "")
            cats = job.get("categories", {})
            location = cats.get("location", "")
            commitment = cats.get("commitment", "")
            matched = keyword_match(title + " " + commitment)
            if matched:
                results.append({"entreprise": company["nom"], "poste": title,
                                 "lieu": location, "lien": link,
                                 "mots_clés": ", ".join(matched[:4]), "source": "Lever"})
    except Exception as e:
        print(f"    ⚠️  {e}")
    return results


def scrape_wttj(company: dict) -> list:
    results = []
    try:
        r = requests.get(company["url"], headers=HEADERS, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        cards = (soup.select("[data-testid='job-card']")
                 or soup.select("li[class*='job']")
                 or soup.select("article"))
        for card in cards:
            title_el = card.select_one("h3, h2, [class*='title']")
            a = card.select_one("a[href]")
            if not title_el or not a:
                continue
            title = title_el.get_text(strip=True)
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.welcometothejungle.com" + href
            matched = keyword_match(title)
            if matched:
                results.append({"entreprise": company["nom"], "poste": title,
                                 "lieu": "France", "lien": href,
                                 "mots_clés": ", ".join(matched[:4]), "source": "WTTJ"})
    except Exception as e:
        print(f"    ⚠️  {e}")
    return results


def scrape_custom(company: dict) -> list:
    results = []
    try:
        r = requests.get(company["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()

        for el in soup.select(
            "li, tr, .job, .offer, .offre, .poste, "
            "[class*='job'], [class*='offer'], [class*='offre'], "
            "[class*='position'], [class*='vacancy']"
        ):
            text = el.get_text(" ", strip=True)
            if len(text) < 8 or len(text) > 300:
                continue
            a = el.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            if any(x in href for x in ["#", "mailto:", "javascript:"]):
                continue
            if not href.startswith("http"):
                href = urljoin(company["url"], href)
            if href in seen:
                continue
            matched = keyword_match(text)
            if matched:
                seen.add(href)
                results.append({"entreprise": company["nom"], "poste": text[:120],
                                 "lieu": "France", "lien": href,
                                 "mots_clés": ", ".join(matched[:4]), "source": "Custom"})

        if not results:
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                href = a["href"]
                if len(text) < 8 or len(text) > 150:
                    continue
                if any(x in href for x in ["#", "mailto:", "javascript:"]):
                    continue
                if not href.startswith("http"):
                    href = urljoin(company["url"], href)
                if href in seen:
                    continue
                matched = keyword_match(text)
                if matched:
                    seen.add(href)
                    results.append({"entreprise": company["nom"], "poste": text[:120],
                                     "lieu": "France", "lien": href,
                                     "mots_clés": ", ".join(matched[:4]), "source": "Custom"})

    except requests.exceptions.Timeout:
        print(f"    ⚠️  Timeout")
    except Exception as e:
        print(f"    ⚠️  {e}")
    return results


# ──────────────────────────────────────────────────────────────
# ORCHESTRATION
# ──────────────────────────────────────────────────────────────

def scrape_all() -> list:
    all_results = []
    total = len(COMPANIES)
    bar = "─" * 62

    print(f"\n┌{bar}┐")
    print(f"│{'SCRAPER STAGES — Infra / Sécu / DevSecOps':^62}│")
    print(f"│{datetime.now().strftime('%d/%m/%Y  %H:%M:%S'):^62}│")
    print(f"│{f'{total} entreprises à scanner':^62}│")
    print(f"└{bar}┘\n")

    scrapers = {
        "greenhouse": scrape_greenhouse,
        "lever":      scrape_lever,
        "wttj":       scrape_wttj,
        "custom":     scrape_custom,
    }

    for i, company in enumerate(COMPANIES, 1):
        label = f"[{i:3}/{total}]  {company['nom']}"
        print(f"{label:<50}", end=" ", flush=True)
        fn = scrapers.get(company.get("type", "custom"), scrape_custom)
        results = fn(company)
        all_results.extend(results)
        if results:
            print(f"✅  {len(results)} offre(s)")
        else:
            print("·")
        time.sleep(1.2)

    return all_results


def export_csv(results: list) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"stages_{ts}.csv"
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["entreprise", "poste", "lieu", "lien", "mots_clés", "source"])
        writer.writeheader()
        writer.writerows(results)
    return filename


def export_json(results: list) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"stages_{ts}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"date": datetime.now().isoformat(), "total": len(results), "offres": results},
                  f, ensure_ascii=False, indent=2)
    return filename


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = scrape_all()
    bar = "─" * 62
    print(f"\n┌{bar}┐")
    print(f"│{f'RÉSULTATS : {len(results)} offre(s) trouvée(s)':^62}│")
    print(f"└{bar}┘\n")

    if results:
        csv_file  = export_csv(results)
        json_file = export_json(results)
        print(f"  ✅ CSV  → {csv_file}")
        print(f"  ✅ JSON → {json_file}\n")
        print(f"  Aperçu (10 premières) :\n")
        for r in results[:10]:
            print(f"  ▸ [{r['entreprise']}] {r['poste'][:55]}")
            print(f"    🔗 {r['lien']}\n")
    else:
        print("  Aucune offre trouvée.")
        print("  → Vérifie les URLs ou ajoute des mots-clés dans KEYWORDS.\n")
