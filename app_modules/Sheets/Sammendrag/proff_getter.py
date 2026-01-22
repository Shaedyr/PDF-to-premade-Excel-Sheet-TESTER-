# app_modules/Sheets/Sammendrag/proff_getter_FIXED.py
"""
FIXED Proff getter - uses updated Proff.no URLs
"""

import re
import logging
from functools import lru_cache
import requests
from bs4 import BeautifulSoup
import streamlit as st

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# UPDATED: Proff.no changed their URLs
BASE_URL = "https://www.proff.no"

def _safe_get(url, params=None, timeout=10):
    try:
        st.write(f"🌐 Fetching: {url}")
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        st.write(f"📊 Status: {r.status_code}")
        
        if r.status_code == 200:
            st.success(f"✅ Success!")
            return r.text
        else:
            st.error(f"❌ Error {r.status_code}")
            
    except Exception as e:
        st.error(f"❌ HTTP error: {e}")
    return None

def _extract_org_no(text):
    m = re.search(r"\b(\d{9})\b", text)
    return m.group(1) if m else None

def _build_company_url(org_number):
    """
    Build direct company page URL using org number.
    Proff.no format: /roller/[org_number]
    """
    return f"{BASE_URL}/roller/{org_number}"

def _parse_financial_table(soup):
    """
    Parse financial table
    """
    st.write("💰 Parsing financial data...")
    
    data = {}
    tables = soup.find_all("table")
    st.write(f"📊 Found {len(tables)} tables")
    
    if not tables:
        return data
    
    # Try to find the financial table
    financial_table = None
    for table in tables:
        # Look for table with financial keywords
        table_text = table.get_text().lower()
        if any(word in table_text for word in ["resultat", "inntekt", "eiendel", "driftsinntekt"]):
            financial_table = table
            st.write("✅ Found financial table")
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
    
    years = list(dict.fromkeys(years))  # Remove duplicates, keep order
    st.write(f"📅 Years found: {years}")
    
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
            
            # Clean the value
            clean_value = re.sub(r"[^\d\-,]", "", value.replace(" ", ""))
            
            # Match financial fields
            if "sum driftsinntekt" in label or "driftsinntekter" in label:
                data[f"sum_driftsinnt_{year}"] = clean_value
                st.write(f"  ✓ Revenue {year}: {clean_value}")
            elif "driftsresultat" in label and "før" not in label:
                data[f"driftsresultat_{year}"] = clean_value
                st.write(f"  ✓ Operating result {year}: {clean_value}")
            elif "resultat før skatt" in label or "ordinært resultat før skatt" in label:
                data[f"ord_res_f_skatt_{year}"] = clean_value
                st.write(f"  ✓ Result before tax {year}: {clean_value}")
            elif "sum eiendeler" in label:
                data[f"sum_eiendeler_{year}"] = clean_value
                st.write(f"  ✓ Total assets {year}: {clean_value}")
    
    return data

def _parse_company_info(soup):
    """
    Extract company info
    """
    st.write("🏢 Parsing company info...")
    
    data = {}
    text = soup.get_text(" ", strip=True)
    
    # Website - look for http links
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if href.startswith("http") and "proff.no" not in href:
            data["homepage"] = href
            st.write(f"  ✓ Homepage: {href}")
            break
    
    # Employees
    employee_match = re.search(r"(?:Ansatte|Antall ansatte)[:\s]+(\d+)", text)
    if employee_match:
        data["employees"] = employee_match.group(1)
        st.write(f"  ✓ Employees: {data['employees']}")
    
    return data

@lru_cache(maxsize=1024)
def fetch_proff_info(org_number: str) -> dict:
    """
    Fetch company info from Proff.no using organization number
    """
    st.write("=" * 50)
    st.write("🚀 FETCHING FROM PROFF.NO (FIXED VERSION)")
    st.write("=" * 50)
    
    if not org_number or not org_number.isdigit():
        st.error("❌ Invalid org number")
        return {}
    
    # Try direct company page URL
    url = _build_company_url(org_number)
    st.write(f"🔗 Company page: {url}")
    
    html = _safe_get(url)
    
    if not html:
        st.error("❌ Could not fetch company page")
        
        # Try alternative: search by org number
        st.write("🔄 Trying alternative method...")
        search_url = f"{BASE_URL}/bransjes%C3%B8k?q={org_number}"
        st.write(f"🔗 Search URL: {search_url}")
        
        html = _safe_get(search_url)
        if not html:
            return {}
        
        # Try to find company link in search results
        soup = BeautifulSoup(html, "html.parser")
        company_link = soup.find("a", href=re.compile(r"/roller/\d+"))
        
        if company_link:
            new_url = BASE_URL + company_link.get("href")
            st.write(f"✅ Found company link: {new_url}")
            html = _safe_get(new_url)
    
    if not html:
        return {}
    
    soup = BeautifulSoup(html, "html.parser")
    
    out = {}
    try:
        financial_data = _parse_financial_table(soup)
        out.update(financial_data)
        
        company_info = _parse_company_info(soup)
        out.update(company_info)
        
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
        st.warning("⚠️ No data was extracted")
        st.info("💡 This company might not have financial data on Proff.no, or the page structure is different than expected.")
    
    return out