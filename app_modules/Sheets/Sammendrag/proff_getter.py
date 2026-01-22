# app_modules/Sheets/Sammendrag/proff_getter.py
"""
Proff.no getter - extracts unique company ID from search results
"""

import re
import json
import logging
from functools import lru_cache
import requests
from bs4 import BeautifulSoup
import streamlit as st

logger = logging.getLogger(__name__)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

BASE_URL = "https://www.proff.no"

def _safe_get(url, timeout=10):
    try:
        st.write(f"🌐 Fetching: {url}")
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        st.write(f"📊 Status: {r.status_code}")
        
        if r.status_code == 200:
            st.success(f"✅ Success!")
            return r.text, r.url
        else:
            st.error(f"❌ Error {r.status_code}")
            
    except Exception as e:
        st.error(f"❌ HTTP error: {e}")
    return None, None

def _extract_company_id_from_search(org_number):
    """
    Extract the unique company ID from search results.
    The ID is in the format like 'IF5ITC407TR'
    """
    st.write(f"🔍 Searching for company ID for org: {org_number}")
    
    # Try the search
    search_url = f"{BASE_URL}/bransjesøk?q={org_number}"
    html, final_url = _safe_get(search_url)
    
    if not html:
        return None
    
    st.write("🔎 Looking for company ID in page source...")
    
    # Look for the unique ID pattern in HTML
    # Pattern: IF followed by alphanumeric, usually in URLs like /selskap/.../IF5ITC407TR
    id_pattern = re.compile(r'/selskap/[^/]+/[^/]+/[^/]+/([A-Z0-9]+)')
    
    matches = id_pattern.findall(html)
    
    if matches:
        st.write(f"📌 Found {len(matches)} potential IDs:")
        for match in matches[:5]:
            st.write(f"  - {match}")
        
        # Use the first one
        company_id = matches[0]
        st.success(f"✅ Using company ID: {company_id}")
        return company_id
    
    # Try alternative: look in script tags for JSON data
    st.write("🔍 Looking in script tags...")
    soup = BeautifulSoup(html, "html.parser")
    
    for script in soup.find_all("script"):
        script_text = script.string
        if script_text and org_number in script_text:
            st.write("📌 Found org number in script tag")
            
            # Try to extract ID from the script
            matches = id_pattern.findall(script_text)
            if matches:
                company_id = matches[0]
                st.success(f"✅ Found ID in script: {company_id}")
                return company_id
    
    # Try another pattern: look for data attributes
    st.write("🔍 Looking in data attributes...")
    for element in soup.find_all(attrs={"data-id": True}):
        data_id = element.get("data-id")
        st.write(f"📌 Found data-id: {data_id}")
        if data_id and len(data_id) > 5:
            return data_id
    
    # Last resort: look for any alphanumeric ID pattern
    st.write("🔍 Looking for any ID pattern...")
    general_id_pattern = re.compile(r'\b([A-Z]{2}\d[A-Z0-9]{8,})\b')
    matches = general_id_pattern.findall(html)
    
    if matches:
        st.write(f"📌 Found potential IDs: {matches[:5]}")
        return matches[0]
    
    st.error("❌ Could not extract company ID")
    
    # DEBUG: Show a sample of the HTML
    with st.expander("🔍 DEBUG: HTML sample"):
        st.code(html[:3000], language="html")
    
    return None

def _build_company_url(company_id):
    """
    We have the ID but not the full URL.
    Try to construct it or search for it.
    """
    # We can't construct the full URL without company name/city/industry
    # So we need to extract it from the search results
    return None

def _find_full_url_from_search(org_number):
    """
    Get the complete company URL from search results
    """
    st.write(f"🔍 Finding full company URL...")
    
    search_url = f"{BASE_URL}/bransjesøk?q={org_number}"
    html, _ = _safe_get(search_url)
    
    if not html:
        return None
    
    # Look for complete URLs in the HTML
    url_pattern = re.compile(r'https://www\.proff\.no/selskap/[^"\'<>\s]+')
    urls = url_pattern.findall(html)
    
    if urls:
        st.write(f"📌 Found {len(urls)} company URLs:")
        for url in urls[:5]:
            st.write(f"  - {url}")
        
        company_url = urls[0]
        st.success(f"✅ Using URL: {company_url}")
        return company_url
    
    st.error("❌ No complete URLs found")
    return None

def _parse_financial_table(soup):
    """
    Parse financial table
    """
    st.write("💰 Parsing financial data...")
    
    data = {}
    tables = soup.find_all("table")
    st.write(f"📊 Found {len(tables)} tables")
    
    if not tables:
        st.warning("⚠️ No tables found")
        return data
    
    # Find financial table
    financial_table = None
    for idx, table in enumerate(tables):
        table_text = table.get_text().lower()
        if any(word in table_text for word in ["resultat", "inntekt", "eiendel", "driftsinntekt", "regnskap"]):
            financial_table = table
            st.write(f"✅ Found financial table (#{idx+1})")
            break
    
    if not financial_table:
        st.warning("⚠️ No financial table found")
        return data
    
    # Extract years
    years = []
    for th in financial_table.find_all("th"):
        year_match = re.search(r"(202\d)", th.get_text())
        if year_match:
            years.append(year_match.group(1))
    
    years = list(dict.fromkeys(years))
    st.write(f"📅 Years: {years}")
    
    # Parse rows
    for row in financial_table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        
        label = cells[0].get_text(strip=True).lower()
        
        for i, year in enumerate(years):
            if i + 1 >= len(cells):
                continue
            
            value = cells[i + 1].get_text(strip=True)
            if not value or value == "-":
                continue
            
            clean_value = re.sub(r"[^\d\-,]", "", value.replace(" ", ""))
            
            if "sum driftsinntekt" in label or "driftsinntekter" in label or "omsetning" in label:
                data[f"sum_driftsinnt_{year}"] = clean_value
                st.write(f"  ✓ Revenue {year}: {clean_value}")
            elif "driftsresultat" in label and "før" not in label:
                data[f"driftsresultat_{year}"] = clean_value
                st.write(f"  ✓ Operating result {year}: {clean_value}")
            elif "resultat før skatt" in label or "ordinært resultat" in label:
                data[f"ord_res_f_skatt_{year}"] = clean_value
                st.write(f"  ✓ Result before tax {year}: {clean_value}")
            elif "sum eiendeler" in label or "totale eiendeler" in label:
                data[f"sum_eiendeler_{year}"] = clean_value
                st.write(f"  ✓ Total assets {year}: {clean_value}")
    
    return data

@lru_cache(maxsize=1024)
def fetch_proff_info(org_number: str) -> dict:
    """
    Fetch financial data from Proff.no
    """
    st.write("=" * 50)
    st.write("🚀 FETCHING FROM PROFF.NO")
    st.write("=" * 50)
    
    if not org_number or not org_number.isdigit():
        st.error("❌ Invalid org number")
        return {}
    
    # Find the complete company URL from search
    company_url = _find_full_url_from_search(org_number)
    
    if not company_url:
        st.error("❌ Could not find company URL")
        st.info(f"💡 Please visit: https://www.proff.no and search for: {org_number}")
        return {}
    
    # Fetch the company page
    html, final_url = _safe_get(company_url)
    
    if not html:
        st.error("❌ Could not fetch company page")
        return {}
    
    soup = BeautifulSoup(html, "html.parser")
    
    out = {}
    try:
        financial_data = _parse_financial_table(soup)
        out.update(financial_data)
        
    except Exception as e:
        st.error(f"❌ Parsing error: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    st.write("=" * 50)
    st.write(f"✅ DONE! Fetched {len(out)} fields")
    st.write("=" * 50)
    
    if out:
        st.json(out)
    else:
        st.warning("⚠️ No financial data extracted")
    
    return out
