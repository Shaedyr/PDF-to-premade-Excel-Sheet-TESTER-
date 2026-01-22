# app_modules/Sheets/Sammendrag/proff_getter.py
"""
Full Proff getter implementation placed inside the Sammendrag sheet folder.
This is a self-contained scraper/normalizer for proff.no company pages.
"""

import re
import logging
from functools import lru_cache
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SammendragBot/1.0)"}
SEARCH_URL = "https://www.proff.no/sok/"
BASE_URL = "https://www.proff.no"

def _safe_get(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
        logger.debug("Request to %s returned %s", url, r.status_code)
    except Exception as e:
        logger.warning("HTTP request failed for %s: %s", url, e)
    return None

def _extract_org_no(text):
    m = re.search(r"\b(\d{9})\b", text)
    return m.group(1) if m else None

def _find_company_page(query):
    """
    Search Proff and return the first company page URL found for the query.
    Query can be orgnr or company name.
    """
    html = _safe_get(SEARCH_URL, params={"q": query})
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    # Proff search results link pattern contains '/selskap/'
    link = soup.select_one("a[href*='/selskap/']")
    if not link:
        # try alternative selector
        link = soup.select_one("a.result-item, a.search-result")
    if not link:
        return None
    href = link.get("href")
    if href and href.startswith("/"):
        href = BASE_URL + href
    logger.info("Proff: found company page %s for query %s", href, query)
    return href

def _parse_financial_table(soup):
    """
    Parse the main financial table(s) and return normalized keys:
    sum_driftsinnt_{year}, driftsresultat_{year}, ord_res_f_skatt_{year}, sum_eiendeler_{year}
    """
    data = {}
    # Try common table classes, fallback to first table
    table = soup.select_one("table.financial-table, table.regnskapstall, table.table-responsive") or soup.find("table")
    if not table:
        return data

    # Extract years from header cells
    years = []
    for th in table.find_all("th"):
        year = re.sub(r"\D", "", th.get_text())
        if year:
            years.append(year)
    # Keep only relevant recent years if present
    years = [y for y in years if y in ("2024", "2023", "2022")] or years[:3]

    for row in table.find_all("tr"):
        cells_all = row.find_all(["th", "td"])
        if not cells_all:
            continue
        label = cells_all[0].get_text(strip=True).lower()
        cells = [c.get_text(strip=True).replace("\xa0", " ").strip() for c in cells_all[1:]]
        for i, year in enumerate(years):
            if i >= len(cells):
                continue
            value = cells[i]
            if not value:
                continue
            # Normalize numeric formatting: remove spaces, non-digit except - and ,
            norm = re.sub(r"[^\d\-,\.]", "", value)
            # Map labels to keys
            if "sum driftsinn" in label or "driftsinntekter" in label or "sum driftsinntekter" in label:
                data[f"sum_driftsinnt_{year}"] = norm
            elif "driftsresultat" in label:
                data[f"driftsresultat_{year}"] = norm
            elif "resultat før skatt" in label or "ordinært resultat" in label:
                data[f"ord_res_f_skatt_{year}"] = norm
            elif "sum eiendeler" in label or "eiendeler" in label:
                data[f"sum_eiendeler_{year}"] = norm
    return data

def _parse_company_info(soup):
    """
    Extract company-level info: website, short economy summary, current insurer, anbudsfrist, employees
    """
    data = {}
    # Website: look for explicit http links in company info area
    link = soup.select_one(".company-info a[href^='http'], .company-details a[href^='http'], a.company-website[href^='http']")
    if link and link.get("href"):
        data["website"] = link["href"].strip()

    text = soup.get_text(" ", strip=True)
    # Current insurer (if present in text)
    m = re.search(r"Dagens selskap[:\s]+([A-Za-z0-9 .\-]+)", text)
    if m:
        data["current_insurer"] = m.group(1).strip()
    # Anbudsfrist (deadline)
    m = re.search(r"Anbudsfrist[:\s]+([0-9.\-]+)", text)
    if m:
        data["anbudsfrist"] = m.group(1).strip()
    # Economy summary heuristics
    m = re.search(r"Økonomi[:\s]+(.+?)(?:\s{2,}|$)", text)
    if m:
        data["economy_summary"] = m.group(1).strip()
    # Employees: try to find "Ansatte" or "Antall ansatte"
    m = re.search(r"(?:Ansatte|Antall ansatte)[:\s]+(\d+)", text)
    if m:
        data["employees"] = m.group(1)
    # Try to extract orgnr from page text if present
    org = _extract_org_no(text)
    if org:
        data["org_no"] = org
    return data

@lru_cache(maxsize=1024)
def fetch_proff_info(query: str) -> dict:
    """
    Public function: given a query (orgnr or name), return a dict with financials and company info.
    """
    if not query:
        return {}
    # If query is an orgnr, try to find page by orgnr first (Proff search supports it)
    url = _find_company_page(query)
    if not url:
        return {}
    html = _safe_get(url)
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    try:
        out.update(_parse_financial_table(soup))
        out.update(_parse_company_info(soup))
    except Exception as e:
        logger.warning("Error parsing Proff page %s: %s", url, e)
    # Ensure org_no exists if possible
    if "org_no" not in out:
        out["org_no"] = _extract_org_no(soup.get_text(" ", strip=True))
    return out