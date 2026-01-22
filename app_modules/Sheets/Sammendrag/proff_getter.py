# app_modules/Sheets/Sammendrag/proff_getter.py
"""
Proff.no getter - properly navigates from search to company page
"""

import re
import logging
from functools import lru_cache
import requests
from bs4 import BeautifulSoup
import streamlit as st

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

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

def _find_company_page_from_search(org_number):
    """
    Search for company and extract the actual company page URL
    """
    st.write(f"🔍 Searching for org number: {org_number}")
    
    # Try the search URL
    search_url = f"{BASE_URL}/bransjes%C3%B8k?q={org_number}"
    html = _safe_get(search_url)
    
    if not html:
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    st.write("🔎 Looking for company links in search results...")
    
    # Try multiple patterns to find company links
    patterns_to_try = [
        re.compile(r"/roller/\d+"),
        re.compile(r"/selskap/[^/]+/\d+"),
        re.compile(r"/foretak/[^/]+/\d+"),
    ]
    
    for pattern in patterns_to_try:
        links = soup.find_all("a", href=pattern)
        st.write(f"📌 Pattern {pattern.pattern}: found {len(links)} links")
        
        if links:
            # Show all found links
            for i, link in enumerate(links[:5]):  # Show first 5
                href = link.get("href")
                link_text = link.get_text(strip=True)
                st.write(f"  {i+1}. Link: {href} - Text: {link_text}")
            
            # Use the first link
            company_href = links[0].get("href")
            
            # Make sure it's a full URL
            if company_href.startswith("/"):
                company_href = BASE_URL + company_href
            
            st.success(f"✅ Found company page: {company_href}")
            return company_href
    
    st.error("❌ No company links found in search results")
    
    # DEBUG: Show what links ARE there
    with st.expander("🔍 DEBUG: All links found on search page"):
        all_links = soup.find_all("a", href=True)
        for link in all_links[:20]:  # Show first 20 links
            st.write(f"- {link.get('href')} → {link.get_text(strip=True)[:50]}")
    
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
        st.warning("⚠️ No tables found on page")
        return data
    
    # Try to find the financial table
    financial_table = None
    for idx, table in enumerate(tables):
        # Look for table with financial keywords
        table_text = table.get_text().lower()
        if any(word in table_text for word in ["resultat", "inntekt", "eiendel", "driftsinntekt"]):
            financial_table = table
            st.write(f"✅ Found financial table (table #{idx+1})")
            break
    
    if not financial_table:
        st.warning("⚠️ No financial table found")
        
        # DEBUG: Show what's in the tables
        with st.expander("🔍 DEBUG: Table contents"):
            for idx, table in enumerate(tables[:3]):  # First 3 tables
                st.write(f"**Table {idx+1}:**")
                rows = table.find_all("tr")[:5]  # First 5 rows
                for row in rows:
                    cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    st.write(cells)
        
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

@lru_cache(maxsize=1024)
def fetch_proff_info(org_number: str) -> dict:
    """
    Fetch financial data from Proff.no using organization number.
    Returns revenue, operating result, result before tax, and total assets for 2024, 2023, 2022.
    """
    st.write("=" * 50)
    st.write("🚀 FETCHING FINANCIAL DATA FROM PROFF.NO")
    st.write("=" * 50)
    
    if not org_number or not org_number.isdigit():
        st.error("❌ Invalid org number")
        return {}
    
    # Find the company page URL via search
    company_url = _find_company_page_from_search(org_number)
    
    if not company_url:
        st.error("❌ Could not find company page")
        return {}
    
    # Now fetch the ACTUAL company page
    st.write("📄 Fetching company page...")
    html = _safe_get(company_url)
    
    if not html:
        st.error("❌ Could not fetch company page")
        return {}
    
    soup = BeautifulSoup(html, "html.parser")
    
    out = {}
    try:
        # Parse financial data
        financial_data = _parse_financial_table(soup)
        out.update(financial_data)
        
    except Exception as e:
        st.error(f"❌ Parsing error: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    st.write("=" * 50)
    st.write(f"✅ DONE! Fetched {len(out)} financial fields")
    st.write("=" * 50)
    
    if out:
        st.json(out)
    else:
        st.warning("⚠️ No financial data was extracted")
        st.info("💡 This company might not have financial data on Proff.no")
    
    return out