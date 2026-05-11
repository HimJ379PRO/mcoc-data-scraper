from typing import Any

from playwright.sync_api import Page, sync_playwright


TABLE_EXTRACTION_SCRIPT = """
({ sectionId }) => {
  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
  const cleanImageLabel = (value) => normalize(value)
    .replace(/\\s+portrait$/i, '')
    .replace(/^Image:\\s*/i, '');

  const cellParts = (cell) => {
    const directText = normalize(cell.innerText);
    if (directText) return [directText];

    const parts = [];

    for (const anchor of cell.querySelectorAll('a')) {
      const text = normalize(anchor.innerText);
      const title = normalize(anchor.getAttribute('title'));
      const label = text || cleanImageLabel(title);
      if (label && !parts.includes(label)) parts.push(label);
    }

    for (const image of cell.querySelectorAll('img')) {
      const label = cleanImageLabel(
        image.getAttribute('alt') ||
        image.getAttribute('data-image-name') ||
        image.getAttribute('title')
      );
      if (label && !parts.includes(label)) parts.push(label);
    }

    return parts;
  };

  const cellText = (cell) => cellParts(cell).join(', ');
  const firstMeaningfulLink = (cell) => {
    for (const anchor of cell.querySelectorAll('a')) {
      const text = normalize(anchor.innerText);
      const title = cleanImageLabel(anchor.getAttribute('title'));
      const label = text || title;
      if (label) return label;
    }
    return '';
  };

  const heading = document.querySelector(`#${CSS.escape(sectionId)}`);
  if (!heading) {
    throw new Error(`Could not find section heading #${sectionId}`);
  }

  let node = heading.closest('h2, h3, h4') || heading.parentElement;
  while (node && node.nextElementSibling) {
    node = node.nextElementSibling;
    if (/^H[23]$/i.test(node.tagName)) break;
    if (node.matches && node.matches('table')) break;
    const nestedTable = node.querySelector && node.querySelector('table');
    if (nestedTable) {
      node = nestedTable;
      break;
    }
  }

  if (!node || !node.matches || !node.matches('table')) {
    throw new Error(`Could not find table after #${sectionId}`);
  }

  const rows = [];
  for (const tr of node.querySelectorAll('tr')) {
    const cells = [...tr.querySelectorAll('th, td')];
    if (cells.length === 0) continue;
    rows.push(cells.map((cell) => ({
      text: cellText(cell),
      firstLink: firstMeaningfulLink(cell),
      links: [...cell.querySelectorAll('a')]
        .map((a) => normalize(a.innerText) || cleanImageLabel(a.getAttribute('title')))
        .filter(Boolean),
    })));
  }
  return rows;
}
"""


def extract_fandom_tables(
    url: str,
    section_ids: list[str],
    headless: bool = True,
) -> dict[str, list[list[dict[str, Any]]]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        _ensure_article_content(page, url, section_ids[0])

        tables = {
            section_id: page.evaluate(TABLE_EXTRACTION_SCRIPT, {"sectionId": section_id})
            for section_id in section_ids
        }
        browser.close()

    return tables


def clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def is_header_row(row: list[dict[str, Any]]) -> bool:
    joined = " ".join(clean_text(cell["text"]).casefold() for cell in row)
    return "description" in joined and ("name" in joined or "buff" in joined)


def dedupe_rows(rows):
    seen = set()
    deduped = []
    for row in rows:
        if row.key in seen:
            continue
        seen.add(row.key)
        deduped.append(row)
    return deduped


def _ensure_article_content(page: Page, url: str, expected_section_id: str) -> None:
    if _is_cloudflare_challenge(page):
        _load_mediawiki_parse_api(page, url, expected_section_id)
        return

    try:
        page.wait_for_selector(
            f".mw-parser-output, #{expected_section_id}",
            state="attached",
            timeout=30_000,
        )
    except Exception:
        _load_mediawiki_parse_api(page, url, expected_section_id)


def _is_cloudflare_challenge(page: Page) -> bool:
    title = clean_text(page.title()).casefold()
    return "just a moment" in title or "__cf_chl" in page.url


def _load_mediawiki_parse_api(page: Page, url: str, expected_section_id: str) -> None:
    api_url = _mediawiki_parse_api_url(url)
    response = page.context.request.get(
        api_url,
        timeout=60_000,
        headers={"Accept": "application/json"},
    )
    if not response.ok:
        raise RuntimeError(f"Fandom MediaWiki API fallback failed: HTTP {response.status}")

    data = response.json()
    html = data.get("parse", {}).get("text", {}).get("*", "")
    if not html:
        raise RuntimeError("Fandom MediaWiki API fallback returned no parse HTML.")

    page.set_content(html, wait_until="domcontentloaded")
    page.wait_for_selector(
        f".mw-parser-output, #{expected_section_id}",
        state="attached",
        timeout=30_000,
    )


def _mediawiki_parse_api_url(page_url: str) -> str:
    base = page_url.split("/wiki/", 1)[0]
    page_name = page_url.rsplit("/wiki/", 1)[-1].split("#", 1)[0].split("?", 1)[0] or "Buff"
    return f"{base}/api.php?action=parse&page={page_name}&prop=text&format=json"
