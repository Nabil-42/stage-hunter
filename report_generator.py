"""
Génère un rapport HTML visuel à partir des offres scorées.
"""

import hashlib
from datetime import datetime


def _source_groupe(source):
    """Regroupe les variantes Jooble sous un seul label."""
    if source.startswith("Jooble"):
        return "Jooble"
    return source


def generate_html_report(offres, profil, output_path="rapport_stages.html"):
    """Génère un fichier HTML avec toutes les offres triées par score."""

    # ── Stats globales ────────────────────────────────────────
    total     = len(offres)
    excellent = [o for o in offres if o["score"] >= 70]
    bon       = [o for o in offres if 40 <= o["score"] < 70]
    faible    = [o for o in offres if o["score"] < 40]
    nb_stages = len([o for o in offres if o.get("type_contrat") == "Stage"])
    nb_cdds   = len([o for o in offres if o.get("type_contrat") == "CDD"])

    # ── Stats par source (groupées) ───────────────────────────
    sources_detail = {}
    for o in offres:
        grp = _source_groupe(o["source"])
        if grp not in sources_detail:
            sources_detail[grp] = {"total": 0, "stages": 0, "cdds": 0}
        sources_detail[grp]["total"] += 1
        tc = o.get("type_contrat", "")
        if tc == "Stage":
            sources_detail[grp]["stages"] += 1
        elif tc == "CDD":
            sources_detail[grp]["cdds"] += 1

    # ── Génération des cartes ─────────────────────────────────
    cards_html = ""
    for i, offre in enumerate(offres):
        score = offre["score"]

        if score >= 70:
            score_class = "score-excellent"
            badge_label = "Excellent match"
        elif score >= 40:
            score_class = "score-bon"
            badge_label = "Bon match"
        else:
            score_class = "score-faible"
            badge_label = "Match partiel"

        tags_html = ""
        for mot in offre.get("mots_trouves", [])[:8]:
            tags_html += f'<span class="tag">{mot}</span>'

        desc = offre.get("description", "Aucune description disponible.")
        desc_courte = desc[:300] + "..." if len(desc) > 300 else desc
        desc_courte = desc_courte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        date_str = offre.get("date_publi", "")
        if date_str:
            try:
                d = datetime.strptime(date_str[:10], "%Y-%m-%d")
                date_aff = d.strftime("%d/%m/%Y")
            except:
                date_aff = date_str
        else:
            date_aff = "—"

        contrat = offre.get("type_contrat", "")
        contrat_class = "contrat-cdd" if contrat == "CDD" else "contrat-stage"

        # On utilise le groupe source pour le data-attribute (filtrage)
        source_grp = _source_groupe(offre["source"])
        source_css = source_grp.lower().replace(" ", "_")

        # ID unique pour le système de masquage (basé sur l'URL ou titre+entreprise)
        key_source = offre.get("url") or f"{offre['titre']}_{offre['entreprise']}"
        card_id = hashlib.md5(key_source.encode("utf-8")).hexdigest()[:12]

        cards_html += f"""
        <div class="card" data-score="{score}" data-source="{source_grp}" data-contrat="{contrat}" data-card-id="{card_id}">
            <div class="card-header">
                <div class="card-title-block">
                    <span class="card-num">#{i+1}</span>
                    <div>
                        <h3 class="card-title">{offre['titre']}</h3>
                        <p class="card-company">{offre['entreprise']} — <span class="card-location">{offre['lieu']}</span></p>
                    </div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.5rem">
                    <button class="btn-masquer" onclick="hideOffer('{card_id}')" title="Ne plus afficher cette offre">✕ Masquer</button>
                    <div class="score-block {score_class}">
                        <span class="score-num">{score}</span>
                        <span class="score-max">/100</span>
                        <span class="score-badge">{badge_label}</span>
                    </div>
                </div>
            </div>

            <div class="card-meta">
                <span class="meta-item">📅 {date_aff}</span>
                <span class="meta-item">📍 {offre['lieu'] or '—'}</span>
                <span class="contrat-badge {contrat_class}">{contrat or '—'}</span>
                <span class="meta-item">💰 {offre.get('salaire', '—')}</span>
                <span class="source-badge source-{source_css}">{offre['source']}</span>
            </div>

            <div class="card-skills">
                {tags_html if tags_html else '<span class="no-tags">Aucune compétence clé détectée</span>'}
            </div>

            <p class="card-desc">{desc_courte}</p>

            <a href="{offre['url']}" target="_blank" class="card-btn">
                Voir l'offre →
            </a>
        </div>
        """

    # ── Stats HTML par source ─────────────────────────────────
    sources_stats_html = ""
    source_colors = {
        "France Travail":         "#58a6ff",
        "Adzuna":                 "#3fb950",
        "Jooble":                 "#d29922",
        "LinkedIn":               "#0a66c2",
        "SmartRecruiters":         "#e8441a",
        "Lever":                   "#695de8",
        "Greenhouse":              "#24a148",
        "PASS Fonction Publique":  "#1a6b3c",
        "Stages IDF":              "#c0392b",
        "Welcome to the Jungle":   "#4a154b",
        "Stage.fr":                "#e05c1a",
    }
    for grp, counts in sources_detail.items():
        color = source_colors.get(grp, "#8b949e")
        detail_parts = []
        if counts["stages"] > 0:
            detail_parts.append(f'<span style="color:#79c0ff">{counts["stages"]} stages</span>')
        if counts["cdds"] > 0:
            detail_parts.append(f'<span style="color:#d2a8ff">{counts["cdds"]} CDD</span>')
        autres = counts["total"] - counts["stages"] - counts["cdds"]
        if autres > 0:
            detail_parts.append(f'<span style="color:#8b949e">{autres} autres</span>')
        detail_str = " · ".join(detail_parts) if detail_parts else ""

        sources_stats_html += f"""
        <div class="source-stat-block">
            <div class="source-stat-name" style="color:{color}">{grp}</div>
            <div class="source-stat-total">{counts["total"]} offres</div>
            <div class="source-stat-detail">{detail_str}</div>
        </div>
        """

    # ── Boutons filtres source ────────────────────────────────
    source_filter_btns = ""
    for grp, counts in sources_detail.items():
        source_filter_btns += f'<button class="filter-btn" data-filter="source" data-value="{grp}" onclick="toggleFilter(this)">{grp} ({counts["total"]})</button>\n  '

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stage Hunter — Rapport Nabil Abboud</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg:       #0d1117;
    --surface:  #161b22;
    --border:   #30363d;
    --text:     #e6edf3;
    --muted:    #8b949e;
    --accent:   #58a6ff;
    --green:    #3fb950;
    --yellow:   #d29922;
    --red:      #f85149;
    --orange:   #e3781a;
    --font-mono: 'JetBrains Mono', monospace;
    --font-main: 'Syne', sans-serif;
  }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-main);
    min-height: 100vh;
    line-height: 1.6;
  }}

  /* ── Header ── */
  .header {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 2rem 2.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
  }}
  .header-logo {{ font-family: var(--font-mono); font-size: 0.85rem; color: var(--accent); letter-spacing: 0.1em; text-transform: uppercase; }}
  .header h1 {{ font-size: 1.6rem; font-weight: 800; letter-spacing: -0.02em; }}
  .header-meta {{ font-family: var(--font-mono); font-size: 0.78rem; color: var(--muted); text-align: right; }}

  /* ── Stats Bar ── */
  .stats-bar {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 1.4rem 2.5rem;
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
    align-items: flex-start;
  }}
  .stat-block {{ display: flex; flex-direction: column; gap: 0.1rem; }}
  .stat-block .num {{ font-family: var(--font-mono); font-size: 1.6rem; font-weight: 700; line-height: 1; }}
  .stat-block .lbl {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }}
  .num-green {{ color: var(--green); }}
  .num-yellow {{ color: var(--yellow); }}
  .num-muted {{ color: var(--muted); }}
  .num-accent {{ color: var(--accent); }}
  .stat-divider {{ width: 1px; height: 48px; background: var(--border); align-self: center; }}

  /* ── Stats par source ── */
  .sources-detail {{
    display: flex;
    gap: 1.2rem;
    flex-wrap: wrap;
    margin-left: auto;
    align-items: flex-start;
  }}
  .source-stat-block {{
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.6rem 1rem;
    min-width: 140px;
  }}
  .source-stat-name {{ font-family: var(--font-mono); font-size: 0.78rem; font-weight: 700; margin-bottom: 0.15rem; }}
  .source-stat-total {{ font-family: var(--font-mono); font-size: 1.1rem; font-weight: 700; color: var(--text); }}
  .source-stat-detail {{ font-family: var(--font-mono); font-size: 0.7rem; margin-top: 0.15rem; }}

  /* ── Filters ── */
  .filters {{
    padding: 1rem 2.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }}
  .filter-row {{
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    align-items: center;
  }}
  .filter-label {{
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--muted);
    min-width: 60px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .filter-btn {{
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    padding: 0.3rem 0.8rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .filter-btn:hover {{ background: rgba(88,166,255,0.1); border-color: var(--accent); color: var(--text); }}
  .filter-btn.active {{ background: var(--accent); border-color: var(--accent); color: #0d1117; font-weight: 700; }}
  .filter-btn[data-filter="contrat"][data-value="Stage"].active {{ background: #79c0ff; border-color: #79c0ff; }}
  .filter-btn[data-filter="contrat"][data-value="CDD"].active {{ background: #d2a8ff; border-color: #d2a8ff; }}
  .filter-btn[data-filter="score"][data-value="excellent"].active {{ background: var(--green); border-color: var(--green); }}
  .filter-btn[data-filter="score"][data-value="bon"].active {{ background: var(--yellow); border-color: var(--yellow); }}

  /* Compteur résultats */
  .filter-count {{
    margin-left: auto;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--muted);
    align-self: center;
  }}
  .filter-count span {{ color: var(--accent); font-weight: 700; }}

  /* ── Container ── */
  .container {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 2rem 2.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }}

  /* ── Card ── */
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.4rem 1.6rem;
    transition: border-color 0.2s, transform 0.15s;
  }}
  .card:hover {{ border-color: var(--accent); transform: translateY(-1px); }}

  .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 0.8rem; }}
  .card-title-block {{ display: flex; align-items: flex-start; gap: 0.8rem; }}
  .card-num {{ font-family: var(--font-mono); font-size: 0.75rem; color: var(--muted); min-width: 28px; padding-top: 3px; }}
  .card-title {{ font-size: 1.05rem; font-weight: 700; letter-spacing: -0.01em; line-height: 1.3; margin-bottom: 0.2rem; }}
  .card-company {{ font-size: 0.85rem; color: var(--muted); }}
  .card-location {{ color: var(--accent); }}

  .score-block {{ display: flex; flex-direction: column; align-items: flex-end; min-width: 90px; flex-shrink: 0; }}
  .score-num {{ font-family: var(--font-mono); font-size: 2rem; font-weight: 700; line-height: 1; }}
  .score-max {{ font-family: var(--font-mono); font-size: 0.75rem; color: var(--muted); }}
  .score-badge {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.2rem; }}
  .score-excellent .score-num {{ color: var(--green); }}
  .score-excellent .score-badge {{ color: var(--green); }}
  .score-bon .score-num {{ color: var(--yellow); }}
  .score-bon .score-badge {{ color: var(--yellow); }}
  .score-faible .score-num {{ color: var(--muted); }}
  .score-faible .score-badge {{ color: var(--muted); }}

  .card-meta {{ display: flex; gap: 1rem; flex-wrap: wrap; align-items: center; margin-bottom: 0.8rem; }}
  .meta-item {{ font-family: var(--font-mono); font-size: 0.75rem; color: var(--muted); }}

  .source-badge {{
    font-family: var(--font-mono); font-size: 0.7rem;
    padding: 0.15rem 0.5rem; border-radius: 3px; font-weight: 700; margin-left: auto;
  }}
  .source-france_travail {{ background: #1f3a5f; color: #58a6ff; border: 1px solid #30527a; }}
  .source-adzuna {{ background: #1f3a2a; color: #3fb950; border: 1px solid #2a5c3a; }}
  [class^="source-jooble"] {{ background: #2d2a1f; color: #d29922; border: 1px solid #5c4e1a; }}
  .source-linkedin {{ background: #0d2236; color: #70b5f9; border: 1px solid #0a66c2; }}
  .source-smartrecruiters {{ background: #2e1208; color: #f07050; border: 1px solid #e8441a; }}
  .source-lever {{ background: #1a1640; color: #9b8ff5; border: 1px solid #695de8; }}
  .source-greenhouse {{ background: #0a2010; color: #4dd17a; border: 1px solid #24a148; }}
  .source-pass_fonction_publique {{ background: #0f2e1a; color: #5dbf85; border: 1px solid #1a6b3c; }}
  .source-stages_idf {{ background: #2e0f0f; color: #e87070; border: 1px solid #c0392b; }}
  .source-welcome_to_the_jungle {{ background: #2a1f2e; color: #c084e0; border: 1px solid #4a154b; }}
  .source-stage_fr {{ background: #2e1a0e; color: #f08050; border: 1px solid #e05c1a; }}

  .contrat-badge {{
    font-family: var(--font-mono); font-size: 0.68rem;
    padding: 0.15rem 0.5rem; border-radius: 3px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.05em;
  }}
  .contrat-stage {{ background: #1a2a3a; color: #79c0ff; border: 1px solid #1e3a5f; }}
  .contrat-cdd   {{ background: #2a1f3a; color: #d2a8ff; border: 1px solid #3a2a5f; }}

  .card-skills {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.8rem; }}
  .tag {{ font-family: var(--font-mono); font-size: 0.72rem; background: #1c2d3a; color: var(--accent); border: 1px solid #1e3a50; padding: 0.15rem 0.5rem; border-radius: 3px; }}
  .no-tags {{ font-size: 0.78rem; color: var(--muted); font-style: italic; }}

  .card-desc {{ font-size: 0.83rem; color: var(--muted); line-height: 1.5; margin-bottom: 1rem; }}

  .card-btn {{
    display: inline-block; font-family: var(--font-mono); font-size: 0.8rem;
    color: var(--accent); text-decoration: none; border: 1px solid var(--border);
    padding: 0.4rem 1rem; border-radius: 4px; transition: all 0.15s;
  }}
  .card-btn:hover {{ background: var(--accent); color: #0d1117; border-color: var(--accent); }}

  .footer {{ text-align: center; padding: 2rem; font-family: var(--font-mono); font-size: 0.75rem; color: var(--muted); border-top: 1px solid var(--border); }}

  .card.hidden {{ display: none; }}
  .card.hidden-seen {{ display: none; }}
  body.show-hidden .card.hidden-seen {{ display: block; opacity: 0.45; border-style: dashed; }}

  .btn-masquer {{
    background: transparent; border: 1px solid var(--border);
    color: var(--muted); font-family: var(--font-mono); font-size: 0.7rem;
    padding: 0.2rem 0.6rem; border-radius: 4px; cursor: pointer;
    transition: all 0.15s; white-space: nowrap;
  }}
  .btn-masquer:hover {{ background: rgba(248,81,73,0.12); border-color: var(--red); color: var(--red); }}

  .no-results {{ text-align: center; padding: 3rem; color: var(--muted); font-family: var(--font-mono); display: none; }}
  .no-results.visible {{ display: block; }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="header-logo">$ stage-hunter --profile nabil-abboud</div>
    <h1>Rapport Stage & CDD — Admin Sys / Sécu</h1>
  </div>
  <div class="header-meta">
    Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}<br>
    Île-de-France · Rayon {profil['rayon_km']} km · Septembre 2026
  </div>
</div>

<div class="stats-bar">
  <div class="stat-block">
    <span class="num num-accent">{total}</span>
    <span class="lbl">Total</span>
  </div>
  <div class="stat-divider"></div>
  <div class="stat-block">
    <span class="num" style="color:#79c0ff">{nb_stages}</span>
    <span class="lbl">Stages</span>
  </div>
  <div class="stat-block">
    <span class="num" style="color:#d2a8ff">{nb_cdds}</span>
    <span class="lbl">CDD</span>
  </div>
  <div class="stat-divider"></div>
  <div class="stat-block">
    <span class="num num-green">{len(excellent)}</span>
    <span class="lbl">Score ≥70</span>
  </div>
  <div class="stat-block">
    <span class="num num-yellow">{len(bon)}</span>
    <span class="lbl">Score 40-69</span>
  </div>
  <div class="stat-block">
    <span class="num num-muted">{len(faible)}</span>
    <span class="lbl">Score &lt;40</span>
  </div>
  <div class="stat-divider"></div>
  <div class="sources-detail">
    {sources_stats_html}
  </div>
</div>

<div class="filters">
  <div class="filter-row">
    <span class="filter-label">Réinitialiser</span>
    <button class="filter-btn active" data-filter="reset" onclick="toggleFilter(this)">Toutes les offres ({total})</button>
    <div class="filter-count">Affichées : <span id="visible-count">{total}</span> / {total}</div>
  </div>
  <div class="filter-row">
    <span class="filter-label">Contrat</span>
    <button class="filter-btn" data-filter="contrat" data-value="Stage" onclick="toggleFilter(this)">🎓 Stages ({nb_stages})</button>
    <button class="filter-btn" data-filter="contrat" data-value="CDD" onclick="toggleFilter(this)">💼 CDD ({nb_cdds})</button>
  </div>
  <div class="filter-row">
    <span class="filter-label" title="Plusieurs sources peuvent être sélectionnées simultanément">Sources <span style="color:var(--muted);font-size:0.65rem">(cumul ✓)</span></span>
    {source_filter_btns}
    <span id="source-active-count" style="display:none;font-family:var(--font-mono);font-size:0.72rem;color:var(--accent);margin-left:0.5rem"></span>
  </div>
  <div class="filter-row">
    <span class="filter-label">Score</span>
    <button class="filter-btn" data-filter="score" data-value="excellent" onclick="toggleFilter(this)">⭐ ≥ 70 ({len(excellent)})</button>
    <button class="filter-btn" data-filter="score" data-value="bon" onclick="toggleFilter(this)">👍 40 – 69 ({len(bon)})</button>
    <button class="filter-btn" data-filter="score" data-value="faible" onclick="toggleFilter(this)">Score &lt; 40 ({len(faible)})</button>
  </div>
  <div class="filter-row" id="hidden-row" style="display:none">
    <span class="filter-label">Masquées</span>
    <span style="font-family:var(--font-mono);font-size:0.78rem;color:var(--muted)"><span id="hidden-count">0</span> offres masquées</span>
    <button class="filter-btn" id="btn-show-hidden" onclick="toggleShowHidden()">Afficher les masquées</button>
    <button class="filter-btn" onclick="resetHidden()" style="color:var(--red);border-color:var(--red)">Réinitialiser</button>
  </div>
</div>

<div class="container" id="cards-container">
  {cards_html if cards_html else '<p style="color:var(--muted);text-align:center;padding:3rem;">Aucune offre trouvée. Vérifie tes clés API dans le fichier .env</p>'}
  <p class="no-results" id="no-results">Aucune offre ne correspond à cette combinaison de filtres.</p>
</div>

<div class="footer">
  Stage Hunter · Nabil Abboud · {datetime.now().year} · {total} offres analysées
</div>

<script>
  // ── Filtres actifs ────────────────────────────────────────────────────────
  const activeFilters = {{
    contrat: new Set(),
    source:  new Set(),
    score:   new Set(),
  }};

  function toggleFilter(btn) {{
    const type  = btn.dataset.filter;
    const value = btn.dataset.value;

    if (type === 'reset') {{
      Object.values(activeFilters).forEach(s => s.clear());
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyFilters();
      return;
    }}

    if (activeFilters[type].has(value)) {{
      activeFilters[type].delete(value);
      btn.classList.remove('active');
    }} else {{
      activeFilters[type].add(value);
      btn.classList.add('active');
    }}

    const anyActive = Object.values(activeFilters).some(s => s.size > 0);
    document.querySelector('[data-filter="reset"]').classList.toggle('active', !anyActive);

    // Compteur sources actives
    const srcCount = activeFilters.source.size;
    const srcEl    = document.getElementById('source-active-count');
    if (srcEl) {{
      if (srcCount > 1) {{
        srcEl.textContent = `${{srcCount}} sources actives`;
        srcEl.style.display = 'inline';
      }} else {{
        srcEl.style.display = 'none';
      }}
    }}

    applyFilters();
  }}

  function applyFilters() {{
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {{
      const score   = parseInt(card.dataset.score);
      const source  = card.dataset.source;
      const contrat = card.dataset.contrat;
      let show = true;

      if (activeFilters.contrat.size > 0) show = show && activeFilters.contrat.has(contrat);
      if (activeFilters.source.size > 0)  show = show && activeFilters.source.has(source);
      if (activeFilters.score.size > 0) {{
        let scoreOk = false;
        if (activeFilters.score.has('excellent')) scoreOk = scoreOk || score >= 70;
        if (activeFilters.score.has('bon'))       scoreOk = scoreOk || (score >= 40 && score < 70);
        if (activeFilters.score.has('faible'))    scoreOk = scoreOk || score < 40;
        show = show && scoreOk;
      }}
      card.classList.toggle('hidden', !show);
    }});

    updateVisibleCount();
  }}

  // ── Système de masquage (localStorage) ───────────────────────────────────
  const HIDDEN_KEY = 'stage_hunter_hidden';

  function getHiddenIds() {{
    try {{ return JSON.parse(localStorage.getItem(HIDDEN_KEY) || '[]'); }}
    catch {{ return []; }}
  }}

  function hideOffer(cardId) {{
    const ids = getHiddenIds();
    if (!ids.includes(cardId)) {{
      ids.push(cardId);
      localStorage.setItem(HIDDEN_KEY, JSON.stringify(ids));
    }}
    const card = document.querySelector(`[data-card-id="${{cardId}}"]`);
    if (card) card.classList.add('hidden-seen');
    updateHiddenCount();
    updateVisibleCount();
  }}

  function resetHidden() {{
    localStorage.removeItem(HIDDEN_KEY);
    document.querySelectorAll('.card.hidden-seen').forEach(c => c.classList.remove('hidden-seen'));
    document.body.classList.remove('show-hidden');
    document.getElementById('btn-show-hidden').textContent = 'Afficher les masquées';
    updateHiddenCount();
    updateVisibleCount();
  }}

  function toggleShowHidden() {{
    const showing = document.body.classList.toggle('show-hidden');
    document.getElementById('btn-show-hidden').textContent =
      showing ? 'Cacher les masquées' : 'Afficher les masquées';
    updateVisibleCount();
  }}

  function updateHiddenCount() {{
    const count = getHiddenIds().length;
    document.getElementById('hidden-count').textContent = count;
    document.getElementById('hidden-row').style.display = count > 0 ? 'flex' : 'none';
  }}

  function updateVisibleCount() {{
    const showing = document.body.classList.contains('show-hidden');
    let visible = 0;
    document.querySelectorAll('.card').forEach(card => {{
      const filterHidden = card.classList.contains('hidden');
      const seenHidden   = card.classList.contains('hidden-seen') && !showing;
      if (!filterHidden && !seenHidden) visible++;
    }});
    document.getElementById('visible-count').textContent = visible;
    const noResults = document.getElementById('no-results');
    noResults.classList.toggle('visible', visible === 0);
  }}

  // ── Restauration au chargement de la page ────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {{
    const ids = getHiddenIds();
    ids.forEach(cardId => {{
      const card = document.querySelector(`[data-card-id="${{cardId}}"]`);
      if (card) card.classList.add('hidden-seen');
    }});
    updateHiddenCount();
    updateVisibleCount();
  }});
</script>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
