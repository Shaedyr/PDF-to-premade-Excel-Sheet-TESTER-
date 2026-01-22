# app_modules/Sheets/Sammendrag/proff_getter.py
"""
Proff.no getter - tries multiple URL patterns directly
"""

import re
import logging
from functools import lru_cache
import requests
from bs4 import BeautifulSoup
import streamlit as st

logger = logging.getLogger(__name__)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

BASE_URL = "https://www.proff.no"

def _safe_get(url, timeout=10):
    try:
        st.write(f"🌐 Fetching: {url}")
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        st.write(f"📊 Status: {r.status_code}")
        
        if r.status_code == 200:
            st.success(f"✅ Success! Final URL: {r.url}")
            return r.text, r.url
        else:
            st.error(f"❌ Error {r.status_code}")
            
    except Exception as e:
        st.error(f"❌ HTTP error: {e}")
    return None, None

def _try_url_patterns(org_number, company_name=None):
    """
    Try multiple URL patterns to find the company page
    """
    st.write("🔗 Trying different URL patterns...")
    
    # Pattern 1: Direct org number
    patterns = [
        f"{BASE_URL}/selskap/-/{org_number}",
        f"{BASE_URL}/foretak/-/{org_number}",
        f"{BASE_URL}/roller/{org_number}",
        f"{BASE_URL}/bransje/org/{org_number}",
    ]
    
    for pattern in patterns:
        st.write(f"📍 Trying: {pattern}")
        html, final_url = _safe_get(pattern)
        
        if html:
            # Check if this looks like a valid company page
            if "nøkkeltall" in html.lower() or "regnskap" in html.lower() or "resultat" in html.lower():
                st.success(f"✅ Found valid company page!")
                return html, final_url
            else:
                st.warning(f"⚠️ Got a page but doesn't look like company page")
    
    return None, None

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
        
        # Try to find financial data in divs or other structures
        st.write("🔍 Looking for financial data in other structures...")
        text = soup.get_text()
        
        # Try to find numbers with context
        patterns = {
            "sum_driftsinnt": r"(?:driftsinntekt|omsetning)[^\d]*([\d\s]+)",
            "driftsresultat": r"driftsresultat[^\d]*([\d\s\-]+)",
            "ord_res_f_skatt": r"resultat.*?skatt[^\d]*([\d\s\-]+)",
            "sum_eiendeler": r"(?:sum\s+)?eiendel[^\d]*([\d\s]+)"
        }
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, text.lower())
            if matches:
                st.write(f"  Found {key}: {matches[:3]}")
        
        return data
    
    # Try to find the financial table
    financial_table = None
    for idx, table in enumerate(tables):
        table_text = table.get_text().lower()
        if any(word in table_text for word in ["resultat", "inntekt", "eiendel", "driftsinntekt", "regnskap"]):
            financial_table = table
            st.write(f"✅ Found financial table (#{idx+1})")
            break
    
    if not financial_table:
        st.warning("⚠️ No financial table found")
        
        # Show what's in tables
        with st.expander("🔍 DEBUG: Show table contents"):
            for idx, table in enumerate(tables[:3]):
                st.write(f"**Table {idx+1}:**")
                for row in table.find_all("tr")[:5]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    if cells:
                        st.write(cells)
        
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
    row_count = 0
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
                row_count += 1
            elif "driftsresultat" in label and "før" not in label:
                data[f"driftsresultat_{year}"] = clean_value
                st.write(f"  ✓ Operating result {year}: {clean_value}")
                row_count += 1
            elif "resultat før skatt" in label or "ordinært resultat" in label:
                data[f"ord_res_f_skatt_{year}"] = clean_value
                st.write(f"  ✓ Result before tax {year}: {clean_value}")
                row_count += 1
            elif "sum eiendeler" in label or "totale eiendeler" in label:
                data[f"sum_eiendeler_{year}"] = clean_value
                st.write(f"  ✓ Total assets {year}: {clean_value}")
                row_count += 1
    
    if row_count == 0:
        st.warning("⚠️ No financial data extracted from table")
    
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
    
    # Try different URL patterns
    html, final_url = _try_url_patterns(org_number)
    
    if not html:
        st.error("❌ Could not find company page")
        st.info("💡 Try manually visiting: https://www.proff.no and searching for org number: " + org_number)
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
        
        # Suggest manual check
        st.info(f"💡 Please check manually: https://www.proff.no (search for {org_number})")
    
    return out
