#!/usr/bin/env python3
"""
Lit le dernier fichier stages_*.json et génère rapport_stages.html
Usage : python generer_rapport.py
"""

import json
import glob
import os
from datetime import datetime

# ── Trouver le JSON le plus récent ───────────────────────────────
fichiers = sorted(glob.glob("stages_*.json"), reverse=True)
if not fichiers:
    print("Aucun fichier stages_*.json trouve. Lance d'abord scraper_stages.py.")
    exit(1)

json_file = fichiers[0]
print(f"Lecture de : {json_file}")

with open(json_file, encoding="utf-8") as f:
    data = json.load(f)

offres   = data.get("offres", [])
total    = data.get("total", len(offres))
date_run = data.get("date", datetime.now().isoformat())[:10]

# ── Données pour les filtres ──────────────────────────────────────
entreprises = sorted({o["entreprise"] for o in offres})
lieux       = sorted({o.get("lieu", "").strip() for o in offres if o.get("lieu", "").strip()})

# ── Sérialiser les offres pour JS ────────────────────────────────
offres_json = json.dumps(offres, ensure_ascii=False)

# ── Template HTML ─────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rapport Stages — {date_run}</title>
<style>
  :root {{
    --bg: #0f1117; --surface: #1a1d27; --card: #20243a;
    --accent: #4f8ef7; --accent2: #7c3aed;
    --text: #e2e8f0; --muted: #64748b; --border: #2d3348;
    --ok: #22c55e; --warn: #f59e0b;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }}

  /* ── Header ── */
  header {{ background: linear-gradient(135deg, var(--surface) 0%, #12152a 100%);
    border-bottom: 1px solid var(--border); padding: 28px 40px; }}
  header h1 {{ font-size: 1.6rem; font-weight: 700; letter-spacing: .5px; }}
  header h1 span {{ color: var(--accent); }}
  .meta {{ color: var(--muted); font-size: .85rem; margin-top: 6px; }}

  /* ── Stats bar ── */
  .stats {{ display: flex; gap: 16px; padding: 20px 40px; flex-wrap: wrap; }}
  .stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 22px; flex: 1; min-width: 140px; text-align: center; }}
  .stat-num {{ font-size: 2rem; font-weight: 700; color: var(--accent); line-height: 1; }}
  .stat-label {{ font-size: .75rem; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: .5px; }}

  /* ── Filters ── */
  .filters {{ padding: 0 40px 20px; display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }}
  .filters label {{ display: flex; flex-direction: column; gap: 5px; font-size: .8rem; color: var(--muted); text-transform: uppercase; letter-spacing: .4px; }}
  .filters input, .filters select {{
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    border-radius: 8px; padding: 9px 14px; font-size: .9rem; outline: none;
    transition: border-color .2s;
  }}
  .filters input {{ width: 260px; }}
  .filters select {{ min-width: 180px; }}
  .filters input:focus, .filters select:focus {{ border-color: var(--accent); }}
  #count {{ color: var(--muted); font-size: .85rem; align-self: center; margin-left: auto; white-space: nowrap; }}

  /* ── Grid ── */
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 14px; padding: 0 40px 40px; }}

  /* ── Card ── */
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px 20px; display: flex; flex-direction: column; gap: 10px;
    transition: border-color .2s, transform .15s; }}
  .card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .card-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
  .entreprise {{ font-size: .72rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: .6px; color: var(--accent); white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; max-width: 55%; }}
  .lieu-badge {{ background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
    padding: 2px 10px; font-size: .7rem; color: var(--muted); white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; max-width: 44%; }}
  .poste {{ font-size: .95rem; font-weight: 600; line-height: 1.35; color: var(--text); }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .tag {{ background: #1e2a4a; border: 1px solid #2d4070; border-radius: 20px;
    padding: 2px 9px; font-size: .68rem; color: #93b4f7; }}
  .card-footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }}
  .source {{ font-size: .7rem; color: var(--muted); }}
  .btn {{ background: var(--accent); color: #fff; border: none; border-radius: 7px;
    padding: 6px 14px; font-size: .8rem; font-weight: 600; cursor: pointer;
    text-decoration: none; transition: opacity .2s; }}
  .btn:hover {{ opacity: .85; }}

  /* ── Empty state ── */
  .empty {{ grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--muted); }}
  .empty-icon {{ font-size: 3rem; margin-bottom: 12px; }}

  @media (max-width: 600px) {{
    header, .stats, .filters, .grid {{ padding-left: 16px; padding-right: 16px; }}
    .filters input {{ width: 100%; }}
  }}
</style>
</head>
<body>

<header>
  <h1>Rapport <span>Stages</span> — Infra · Sécu · DevSecOps</h1>
  <p class="meta">Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")} · Source : {json_file}</p>
</header>

<div class="stats">
  <div class="stat"><div class="stat-num" id="s-total">{total}</div><div class="stat-label">Offres trouvées</div></div>
  <div class="stat"><div class="stat-num">{len(entreprises)}</div><div class="stat-label">Entreprises</div></div>
  <div class="stat"><div class="stat-num" id="s-visible">—</div><div class="stat-label">Offres affichées</div></div>
</div>

<div class="filters">
  <label>Recherche
    <input type="text" id="q" placeholder="poste, mot-clé…">
  </label>
  <label>Entreprise
    <select id="f-entreprise">
      <option value="">Toutes</option>
      {''.join(f'<option value="{e}">{e}</option>' for e in entreprises)}
    </select>
  </label>
  <label>Lieu
    <select id="f-lieu">
      <option value="">Tous</option>
      {''.join(f'<option value="{l}">{l}</option>' for l in lieux)}
    </select>
  </label>
  <span id="count"></span>
</div>

<div class="grid" id="grid"></div>

<script>
const OFFRES = {offres_json};

function render(list) {{
  const grid = document.getElementById('grid');
  document.getElementById('s-visible').textContent = list.length;
  document.getElementById('count').textContent = list.length + ' offre(s) affichée(s)';
  if (!list.length) {{
    grid.innerHTML = '<div class="empty"><div class="empty-icon">🔍</div>Aucune offre ne correspond aux filtres.</div>';
    return;
  }}
  grid.innerHTML = list.map(o => {{
    const tags = (o.mots_clés || '').split(',').map(t => t.trim()).filter(Boolean)
      .slice(0, 5).map(t => `<span class="tag">${{t}}</span>`).join('');
    const lieu = o.lieu ? `<span class="lieu-badge">${{o.lieu}}</span>` : '';
    return `
      <div class="card">
        <div class="card-top">
          <span class="entreprise">${{o.entreprise}}</span>
          ${{lieu}}
        </div>
        <div class="poste">${{o.poste}}</div>
        ${{tags ? `<div class="tags">${{tags}}</div>` : ''}}
        <div class="card-footer">
          <span class="source">${{o.source || ''}}</span>
          ${{o.lien ? `<a class="btn" href="${{o.lien}}" target="_blank" rel="noopener">Voir l'offre →</a>` : ''}}
        </div>
      </div>`;
  }}).join('');
}}

function filter() {{
  const q   = document.getElementById('q').value.toLowerCase();
  const ent = document.getElementById('f-entreprise').value;
  const loc = document.getElementById('f-lieu').value;
  render(OFFRES.filter(o => {{
    const text = (o.poste + ' ' + o.mots_clés + ' ' + o.entreprise).toLowerCase();
    return (!q || text.includes(q))
        && (!ent || o.entreprise === ent)
        && (!loc || (o.lieu || '').includes(loc));
  }}));
}}

['q','f-entreprise','f-lieu'].forEach(id =>
  document.getElementById(id).addEventListener('input', filter));

render(OFFRES);
</script>
</body>
</html>"""

ts = datetime.now().strftime("%Y%m%d_%H%M")
output = f"rapport_scraper_{ts}.html"
with open(output, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Rapport genere : {output}")
print("   -> Ouvre-le dans ton navigateur (double-clic sur le fichier)")
