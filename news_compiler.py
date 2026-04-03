"""Compile scraped articles into a formatted HTML email body."""

from __future__ import annotations

import io
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable

from utils import Article, log, t


def compile_articles(articles: Iterable[Article], lang: str = "zh") -> tuple[str, int]:
    """Compile *articles* into an HTML email string.

    Returns ``(html_body, total_article_count)``.
    Articles are grouped by source, then rendered into a responsive HTML
    newsletter layout.
    """
    # Group by source (use defaultdict to avoid holding full list)
    grouped: dict[str, list[Article]] = defaultdict(list)
    total = 0
    seen_urls: set[str] = set()

    for art in articles:
        if art.url in seen_urls:
            continue
        seen_urls.add(art.url)
        grouped[art.source].append(art)
        total += 1

    if total == 0:
        log.warning("No articles collected — email will be empty")
        return _empty_email(lang), 0

    # Build HTML
    buf = io.StringIO()
    date_str = datetime.now().strftime("%Y 年 %m 月 %d 日") if lang == "zh" else datetime.now().strftime("%Y-%m-%d")
    
    buf.write(_HEADER_HTML.format(
        report_title=t("report_title", lang),
        report_sub=t("report_sub", lang, d=date_str, t=total),
    ))

    for source, arts in grouped.items():
        buf.write(_section_open(source, len(arts)))
        for art in arts:
            buf.write(_article_html(art))
        buf.write("</div>\n")

    buf.write(_FOOTER_HTML.format(report_footer=t("report_footer", lang)))

    html_body = buf.getvalue()
    buf.close()

    # Free grouped data immediately
    grouped.clear()
    seen_urls.clear()

    log.info("Compiled %d articles into HTML email", total)
    return html_body, total


# ---------------------------------------------------------------------------
# HTML template fragments
# ---------------------------------------------------------------------------

_HEADER_HTML = """\
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{report_title}</title>
<style>
  body {{
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
    background: #f0f2f5; color: #1a1a2e;
    -webkit-font-smoothing: antialiased;
  }}
  .wrapper {{
    max-width: 680px; margin: 0 auto; padding: 24px 12px;
  }}
  .header {{
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    border-radius: 16px 16px 0 0;
    padding: 36px 32px 28px;
    color: #ffffff;
  }}
  .header h1 {{
    margin: 0; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;
  }}
  .header .sub {{
    margin-top: 8px; font-size: 14px; opacity: 0.75;
  }}
  .body-wrap {{
    background: #ffffff;
    border-radius: 0 0 16px 16px;
    padding: 8px 0 24px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
  }}
  .section {{
    padding: 20px 32px 12px;
  }}
  .section-title {{
    font-size: 17px; font-weight: 700; color: #302b63;
    margin: 0 0 6px; padding-bottom: 6px;
    border-bottom: 2px solid #6c63ff;
    display: flex; align-items: center; gap: 8px;
  }}
  .section-count {{
    font-size: 12px; font-weight: 500; color: #6c63ff;
    background: #ede9fe; border-radius: 10px; padding: 2px 9px;
  }}
  .article {{
    margin: 14px 0; padding: 14px 16px;
    background: #fafafa; border-radius: 10px;
    border-left: 3px solid #6c63ff;
    transition: background 0.15s;
  }}
  .article:hover {{ background: #f0edff; }}
  .article-title {{
    font-size: 15px; font-weight: 600; margin: 0 0 4px; line-height: 1.45;
  }}
  .article-title a {{
    color: #1a1a2e; text-decoration: none;
  }}
  .article-title a:hover {{ color: #6c63ff; }}
  .article-meta {{
    font-size: 11px; color: #999; margin: 0 0 6px;
  }}
  .article-meta .tag {{
    display: inline-block; background: #e8f4f8; color: #0077b6;
    border-radius: 4px; padding: 1px 6px; font-size: 10px; margin-right: 6px;
  }}
  .article-summary {{
    font-size: 13px; color: #555; line-height: 1.55; margin: 0;
  }}
  .footer {{
    text-align: center; padding: 24px 16px 8px;
    font-size: 11px; color: #aaa;
  }}
  .footer a {{ color: #6c63ff; text-decoration: none; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>{report_title}</h1>
    <div class="sub">{report_sub}</div>
  </div>
  <div class="body-wrap">
"""

_FOOTER_HTML = """\
    <div class="footer">
      {report_footer}
    </div>
  </div>
</div>
</body>
</html>
"""


def _section_open(source: str, count: int) -> str:
    return (
        f'<div class="section">\n'
        f'  <div class="section-title">{_esc(source)}'
        f'  <span class="section-count">{count}</span></div>\n'
    )


def _article_html(art: Article) -> str:
    parts: list[str] = []
    parts.append(f'<div class="article">\n')
    parts.append(
        f'  <p class="article-title"><a href="{_esc(art.url)}" target="_blank">'
        f'{_esc(art.title)}</a></p>\n'
    )

    # Meta line
    meta_parts: list[str] = []
    if art.category:
        meta_parts.append(f'<span class="tag">{_esc(art.category)}</span>')
    if art.keyword:
        meta_parts.append(f'<span class="tag">🔍 {_esc(art.keyword)}</span>')
    if art.published:
        meta_parts.append(_esc(art.published))
    if meta_parts:
        parts.append(f'  <p class="article-meta">{"  ".join(meta_parts)}</p>\n')

    if art.summary:
        parts.append(f'  <p class="article-summary">{_esc(art.summary)}</p>\n')

    parts.append("</div>\n")
    return "".join(parts)


def _empty_email(lang: str) -> str:
    date_str = datetime.now().strftime("%Y 年 %m 月 %d 日") if lang == "zh" else datetime.now().strftime("%Y-%m-%d")
    
    header = _HEADER_HTML.format(
        report_title=t("report_title", lang),
        report_sub=t("report_sub", lang, d=date_str, t=0),
    )
    
    body = f'<div class="section"><p style="color:#999;padding:24px;">{t("report_no_news", lang)}</p></div>\n'
    
    footer = _FOOTER_HTML.format(report_footer=t("report_footer", lang))
    
    return header + body + footer


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
