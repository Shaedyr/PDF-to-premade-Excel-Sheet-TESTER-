# app_modules/Sheets/Sammendrag/proff_getter_DEBUG.py
"""
DEBUG version of Proff getter - shows exactly what's happening
"""

import re
import logging
from functools import lru_cache
import requests
from bs4 import BeautifulSoup
import streamlit as st

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SammendragBot/1.0)"}
SEARCH_URL = "https://www.proff.no/sok/"
BASE_URL = "https://www.proff.no"

def _safe_get(url, params=None, timeout=10):
    try:
        st.write(f"🌐 Attempting to fetch: {url}")
        if params:
            st.write(f"📋 Parameters: {params}")
        
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        st.write(f"📊 Status: {r.status_code}")
        
        if r.status_code == 200:
            st.success(f"✅ Successfully fetched from {url}")
            return r.text
        else:
            st.error(f"❌ Error status code {r.status_code} from {url}")
            
    except Exception as e:
        st.error(f"❌ HTTP error: {e}")
    return None

def _extract_org_no(text):
    m = re.search(r"\b(\d{9})\b", text)
    result = m.group(1) if m else None
    if result:
        st.write(f"🔢 Found org.nr: {result}")
    return result

def _find_company_page(query):
    """
    Search Proff and return the first company page URL found for the query.
    """
    st.write(f"🔍 Searching for: '{query}'")
    
    html = _safe_get(SEARCH_URL, params={"q": query})
    if not html:
        st.error("❌ Could not fetch search results")
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    # DEBUG: Show what we found
    st.write("🔎 Looking for links with '/selskap/'...")
    
    # Try multiple selectors
    selectors = [
        "a[href*='/selskap/']",
        "a.result-item",
        "a.search-result",
        "a[href*='/bransje/']"
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        st.write(f"📌 Trying selector '{selector}': found {len(links)} links")
        
        if links:
            link = links[0]
            href = link.get("href")
            st.write(f"🔗 First link found: {href}")
            
            if href and href.startswith("/"):
                href = BASE_URL + href
            
            st.success(f"✅ Using page: {href}")
            return href
    
    st.error("❌ Found no company page in search results")
    
    # DEBUG: Show what HTML we got
    with st.expander("🔍 View HTML from search results (for debugging)"):
        st.code(html[:2000], language="html")
    
    return None

def _parse_financial_table(soup):
    """
    Parse financial table and return data
    """
    st.write("💰 Attempting to parse financial table...")
    
    data = {}
    
    # Try to find tables
    tables = soup.find_all("table")
    st.write(f"📊 Found {len(tables)} tables on the page")
    
    if not tables:
        st.warning("⚠️ No tables found")
        return data
    
    # Try common table classes
    table = soup.select_one("table.financial-table, table.regnskapstall, table.table-responsive") or tables[0]
    
    # DEBUG: Show table info
    st.write(f"📋 Using table: {table.get('class', 'no class')}")
    
    # Extract years from header
    years = []
    for th in table.find_all("th"):
        year = re.sub(r"\D", "", th.get_text())
        if year:
            years.append(year)
    
    years = [y for y in years if y in ("2024", "2023", "2022")] or years[:3]
    st.write(f"📅 Years found in table: {years}")
    
    # Parse rows
    row_count = 0
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
            
            # Normalize
            norm = re.sub(r"[^\d\-,\.]", "", value)
            
            # Map labels
            if "sum driftsinn" in label or "driftsinntekter" in label:
                data[f"sum_driftsinnt_{year}"] = norm
                st.write(f"  ✓ Revenue {year}: {norm}")
                row_count += 1
            elif "driftsresultat" in label:
                data[f"driftsresultat_{year}"] = norm
                st.write(f"  ✓ Operating result {year}: {norm}")
                row_count += 1
            elif "resultat før skatt" in label or "ordinært resultat" in label:
                data[f"ord_res_f_skatt_{year}"] = norm
                st.write(f"  ✓ Result before tax {year}: {norm}")
                row_count += 1
            elif "sum eiendeler" in label or "eiendeler" in label:
                data[f"sum_eiendeler_{year}"] = norm
                st.write(f"  ✓ Total assets {year}: {norm}")
                row_count += 1
    
    if row_count == 0:
        st.warning("⚠️ No financial data was extracted from the table")
        
        # Show table content for debugging
        with st.expander("🔍 View table content (for debugging)"):
            for row in table.find_all("tr")[:10]:  # First 10 rows
                cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                st.write(cells)
    
    return data

def _parse_company_info(soup):
    """
    Extract company info
    """
    st.write("🏢 Attempting to parse company information...")
    
    data = {}
    text = soup.get_text(" ", strip=True)
    
    # Website
    link = soup.select_one(".company-info a[href^='http'], .company-details a[href^='http'], a.company-website[href^='http']")
    if link and link.get("href"):
        data["website"] = link["href"].strip()
        st.write(f"  ✓ Website: {data['website']}")
    
    # Employees
    m = re.search(r"(?:Ansatte|Antall ansatte)[:\s]+(\d+)", text)
    if m:
        data["employees"] = m.group(1)
        st.write(f"  ✓ Employees: {data['employees']}")
    
    # Org number
    org = _extract_org_no(text)
    if org:
        data["org_no"] = org
    
    return data

@lru_cache(maxsize=1024)
def fetch_proff_info(query: str) -> dict:
    """
    DEBUG version - shows everything that's happening
    """
    st.write("=" * 50)
    st.write("🚀 STARTING PROFF.NO FETCH (DEBUG MODE)")
    st.write("=" * 50)
    
    if not query:
        st.error("❌ No query provided")
        return {}
    
    # Find company page
    url = _find_company_page(query)
    if not url:
        st.error("❌ Could not find company page")
        return {}
    
    # Fetch company page
    html = _safe_get(url)
    if not html:
        st.error("❌ Could not fetch company page")
        return {}
    
    soup = BeautifulSoup(html, "html.parser")
    
    out = {}
    try:
        # Parse financial data
        financial_data = _parse_financial_table(soup)
        out.update(financial_data)
        
        # Parse company info
        company_info = _parse_company_info(soup)
        out.update(company_info)
        
    except Exception as e:
        st.error(f"❌ Error during parsing: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    st.write("=" * 50)
    st.write(f"✅ DONE! Fetched {len(out)} fields total")
    st.write("=" * 50)
    
    if out:
        st.json(out)
    
    return out