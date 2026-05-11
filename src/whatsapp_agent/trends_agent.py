"""
Subagente especialista em Google Trends BR.

Uso:
    python -m whatsapp_agent.trends_agent               # retorna top trends no stdout
    python -m whatsapp_agent.trends_agent --html <path> # gera dashboard HTML
    python -m whatsapp_agent.trends_agent --geo US      # outro país (default: BR)
    python -m whatsapp_agent.trends_agent --limit 15    # quantos itens (default: 10)
"""

import argparse
import json
import re
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path


GEO_NAMES = {
    "BR": "Brasil",
    "US": "Estados Unidos",
    "PT": "Portugal",
    "AR": "Argentina",
}

SESSION = "trends-agent"
# agent-browser installed via npm — resolve full path for subprocess on Windows
import shutil as _shutil
_AB_BIN = _shutil.which("agent-browser") or "agent-browser"


def _ab(*args: str) -> str:
    """Run agent-browser command, return stdout."""
    result = subprocess.run(
        [_AB_BIN, "--session", SESSION, *args],
        capture_output=True, text=True, timeout=30,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"agent-browser error: {result.stderr.strip()}")
    return result.stdout.strip()


def fetch_trends(geo: str = "BR", limit: int = 10) -> list[dict]:
    """Fetch top trending searches from Google Trends. Returns list of dicts."""
    url = f"https://trends.google.com/trending?geo={geo}"

    try:
        _ab("open", url)
        _ab("wait", "--load", "networkidle")
        snapshot = _ab("snapshot", "-i", "-c")
    finally:
        _ab("close")

    items = []
    current = {}

    for line in snapshot.splitlines():
        # Main trend row
        m_title = re.search(r'gridcell "([^"]{5,})"', line)
        m_volume = re.search(r'gridcell "(\d+\w+\+\s+[\d\.]+%)"', line)

        if m_volume:
            raw = m_volume.group(1)
            parts = raw.split()
            if current:
                current["volume"] = parts[0] if parts else "?"
                current["growth"] = parts[1] if len(parts) > 1 else "+?"
                items.append(current)
                current = {}
        elif m_title:
            text = m_title.group(1)
            skip = {"Selecionar", "Volume", "Gráfico", "Iniciado", "Últimas", "Tendências"}
            if any(s in text for s in skip):
                continue
            if re.search(r"há \d+", text) or text in ("Ativa", "Inativa"):
                continue
            if "Veja mais" in text:
                continue
            if not current:
                current = {"title": text, "volume": "?", "growth": "?", "tags": []}
            elif current.get("title") and len(text) > 3:
                current.setdefault("tags", [])
                if text not in current["tags"] and text != current["title"]:
                    current["tags"].append(text)

    if current and current.get("title"):
        items.append(current)

    # Deduplicate by title
    seen, deduped = set(), []
    for item in items:
        key = item["title"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:limit]


def categorize(title: str) -> tuple[str, str]:
    """Return (emoji, label) for a trend title."""
    t = title.lower()
    football = ["x ", " x", "flamengo", "gremio", "corinthians", "atletico", "palmeiras",
                "fortaleza", "sport", "vitoria", "mirassol", "palestino", "cienciano",
                "nassr", "ahli", "futebol", "libertadores", "copa", "campeonato",
                "classificac", "jogo do", "always ready", "estudiantes", "penharol"]
    finance  = ["itau", "bradesco", "banco", "bolsa", "acao", "financ", "itaucard",
                "nubank", "mercado", "economia", "inflacao"]
    politics = ["veto", "justa causa", "governo", "congresso", "senado", "lula",
                "presidente", "ministerio", "politica", "eleicao"]
    tech     = ["google", "apple", "meta", "ia ", "inteligencia", "iphone", "android"]
    showbiz  = ["novela", "musica", "artista", "cantor", "ator", "atriz", "reality",
                "bbb", "globo", "netflix"]

    if any(k in t for k in football): return "⚽", "Futebol"
    if any(k in t for k in finance):  return "💰", "Finanças"
    if any(k in t for k in politics): return "⚖️", "Política"
    if any(k in t for k in tech):     return "💻", "Tecnologia"
    if any(k in t for k in showbiz):  return "🎬", "Entretenimento"
    return "📰", "Notícias"


def format_text(items: list[dict], geo: str = "BR") -> str:
    """Format trends as plain text for WhatsApp."""
    geo_name = GEO_NAMES.get(geo, geo)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [f"Google Trends {geo_name} — {now}", ""]
    for i, item in enumerate(items, 1):
        emoji, cat = categorize(item["title"])
        vol = item.get("volume", "?")
        lines.append(f"{i}. {emoji} {item['title'].title()} ({vol}) [{cat}]")
    return "\n".join(lines)


def generate_html(items: list[dict], geo: str = "BR", output_path: str | None = None) -> str:
    """Generate and save HTML dashboard. Returns output path."""
    geo_name = GEO_NAMES.get(geo, geo)
    now = datetime.now().strftime("%d de %B de %Y · %H:%M")

    cards_html = ""
    for i, item in enumerate(items, 1):
        emoji, cat = categorize(item["title"])
        top3_class = " top3" if i <= 3 else ""
        vol = item.get("volume", "?")
        growth = item.get("growth", "?")
        tags = item.get("tags", [])
        tags_html = "".join(
            f'<span class="badge badge-tag">{t}</span>' for t in tags[:3]
        )
        cards_html += f"""
    <div class="card{top3_class}">
      <div class="rank">{i}</div>
      <div class="card-body">
        <div class="card-title">{item['title'].title()}</div>
        <div class="badges">
          <span class="badge badge-volume">{vol}</span>
          <span class="badge badge-cat">{emoji} {cat}</span>
          <span class="badge badge-active">● Ativa</span>
          <span class="badge badge-hot">{growth}</span>
          {tags_html}
        </div>
      </div>
    </div>"""

    html = textwrap.dedent(f"""\
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Últimas Notícias — Google Trends {geo_name}</title>
      <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0f0f13; color:#e8e8f0; min-height:100vh; padding:2rem; }}
        header {{ display:flex; align-items:center; gap:1rem; margin-bottom:2rem; padding-bottom:1.5rem; border-bottom:1px solid #2a2a3a; }}
        header h1 {{ font-size:1.6rem; font-weight:700; background:linear-gradient(135deg,#4f8ef7,#a855f7); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
        header .meta {{ margin-left:auto; font-size:0.8rem; color:#6b6b80; }}
        .section-title {{ font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:.1em; color:#6b6b80; margin-bottom:1rem; }}
        .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:1rem; margin-bottom:2rem; }}
        .card {{ background:#16161f; border:1px solid #2a2a3a; border-radius:12px; padding:1.25rem; display:flex; align-items:flex-start; gap:1rem; transition:border-color .2s,transform .2s; }}
        .card:hover {{ border-color:#4f8ef7; transform:translateY(-2px); }}
        .rank {{ font-size:1.4rem; font-weight:800; color:#2a2a3a; min-width:2rem; }}
        .card.top3 .rank {{ color:#f59e0b; }}
        .card-body {{ flex:1; }}
        .card-title {{ font-size:.95rem; font-weight:600; color:#e8e8f0; margin-bottom:.4rem; text-transform:capitalize; }}
        .badges {{ display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.5rem; }}
        .badge {{ font-size:.7rem; font-weight:600; padding:.2rem .55rem; border-radius:99px; }}
        .badge-volume {{ background:#1e2a3a; color:#4f8ef7; border:1px solid #2a3a5a; }}
        .badge-cat {{ background:#1e1e2e; color:#a855f7; border:1px solid #3a2a5a; }}
        .badge-hot {{ background:#2a1a1a; color:#f87171; border:1px solid #5a2a2a; }}
        .badge-active {{ background:#1a2a1a; color:#4ade80; border:1px solid #2a5a2a; }}
        .badge-tag {{ background:#1e1e1e; color:#9b9baa; border:1px solid #2a2a3a; }}
        footer {{ text-align:center; font-size:.75rem; color:#3a3a50; margin-top:2rem; padding-top:1.5rem; border-top:1px solid #2a2a3a; }}
      </style>
    </head>
    <body>
      <header>
        <span style="font-size:2rem">📊</span>
        <div>
          <h1>Últimas Notícias — Google Trends {geo_name}</h1>
          <div style="font-size:.82rem;color:#6b6b80;margin-top:2px;">Atualizado em {now}</div>
        </div>
        <div class="meta">Fonte: Google Trends · {geo_name} · Últimas 24h</div>
      </header>
      <p class="section-title">Top {len(items)} Tendências · {geo_name}</p>
      <div class="grid">{cards_html}
      </div>
      <footer>Gerado por trends_agent.py · Claude Code</footer>
    </body>
    </html>
    """)

    if output_path is None:
        desktop = Path.home() / "Desktop" / "Ultimas Noticias"
        desktop.mkdir(parents=True, exist_ok=True)
        output_path = str(desktop / "index.html")

    Path(output_path).write_text(html, encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Google Trends subagent")
    parser.add_argument("--geo",   default="BR",   help="Country code (BR, US, PT, AR)")
    parser.add_argument("--limit", default=10, type=int, help="Max trends to fetch")
    parser.add_argument("--html",  nargs="?", const="auto", metavar="PATH",
                        help="Generate HTML dashboard (optional output path)")
    parser.add_argument("--json",  action="store_true", help="Output as JSON")
    args = parser.parse_args()

    try:
        items = fetch_trends(geo=args.geo, limit=args.limit)
    except Exception as e:
        print(f"[trends_agent] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    elif args.html is not None:
        path = None if args.html == "auto" else args.html
        out = generate_html(items, geo=args.geo, output_path=path)
        print(f"[trends_agent] Dashboard salvo: {out}")
    else:
        print(format_text(items, geo=args.geo))


if __name__ == "__main__":
    main()
