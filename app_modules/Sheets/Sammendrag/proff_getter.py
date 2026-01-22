# app_modules/Sheets/Sammendrag/proff_getter.py
"""
Selenium-based Proff.no scraper - Streamlit Cloud compatible
"""

import re
import time
import os
from functools import lru_cache
import streamlit as st

# Try to import Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def _get_chrome_options():
    """Get Chrome options configured for Streamlit Cloud"""
    chrome_options = Options()
    
    # Essential options for headless mode
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-features=NetworkService")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    
    return chrome_options


def _get_webdriver():
    """Initialize webdriver - works on both local and Streamlit Cloud"""
    chrome_options = _get_chrome_options()
    
    # Try to use chromium-browser (for Streamlit Cloud/Linux)
    chromium_path = "/usr/bin/chromium-browser"
    if os.path.exists(chromium_path):
        chrome_options.binary_location = chromium_path
        st.write("✅ Using Chromium browser")
        
        # Use chromium driver
        chromium_driver = "/usr/bin/chromedriver"
        if os.path.exists(chromium_driver):
            service = Service(chromium_driver)
            return webdriver.Chrome(service=service, options=chrome_options)
    
    # Fallback to regular Chrome with webdriver-manager
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        st.error(f"Could not initialize Chrome: {e}")
        raise


@lru_cache(maxsize=1024)
def fetch_proff_info(org_number: str) -> dict:
    """
    Fetch financial data from Proff.no using Selenium
    """
    st.write("=" * 50)
    st.write("🚀 FETCHING FROM PROFF.NO WITH SELENIUM")
    st.write("=" * 50)
    
    if not SELENIUM_AVAILABLE:
        st.error("❌ Selenium not installed!")
        st.info("""
        Install Selenium:
        ```
        pip install selenium webdriver-manager
        ```
        
        For Streamlit Cloud: Add `packages.txt` file with:
        ```
        chromium
        chromium-driver
        ```
        """)
        return {}
    
    if not org_number or not org_number.isdigit():
        st.error("❌ Invalid org number")
        return {}
    
    st.write(f"🔍 Searching for org: {org_number}")
    
    driver = None
    try:
        # Set up browser
        st.write("🌐 Setting up browser...")
        driver = _get_webdriver()
        st.write("✅ Browser ready")
        
        # Go to Proff.no search
        search_url = f"https://www.proff.no/bransjesøk?q={org_number}"
        st.write(f"📄 Loading: {search_url}")
        driver.get(search_url)
        
        # Wait for search results
        st.write("⏳ Waiting for search results...")
        time.sleep(5)  # Give more time for JavaScript
        
        # Look for company link
        st.write("🔎 Looking for company link...")
        
        # Try multiple selectors
        selectors = [
            "a[href*='/selskap/']",
            "a[href*='/foretak/']",
            ".company-link",
            ".search-result a"
        ]
        
        company_url = None
        for selector in selectors:
            try:
                links = driver.find_elements(By.CSS_SELECTOR, selector)
                if links:
                    company_url = links[0].get_attribute("href")
                    st.success(f"✅ Found company: {company_url}")
                    break
            except:
                continue
        
        if not company_url:
            st.error("❌ Could not find company link")
            
            # Show page for debugging
            with st.expander("🔍 DEBUG: Page source"):
                st.code(driver.page_source[:2000])
            
            return {}
        
        # Navigate to company page
        st.write("🖱️ Loading company page...")
        driver.get(company_url)
        time.sleep(3)
        
        st.write("📊 Parsing financial data...")
        
        # Get page source and parse
        page_source = driver.page_source
        data = _parse_page_source(page_source)
        
        if data:
            st.write("=" * 50)
            st.write(f"✅ DONE! Fetched {len(data)} financial fields")
            st.write("=" * 50)
            st.json(data)
        else:
            st.warning("⚠️ No financial data found")
        
        return data
        
    except Exception as e:
        st.error(f"❌ Selenium error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return {}
        
    finally:
        # Always close browser
        if driver:
            try:
                driver.quit()
                st.write("🔒 Browser closed")
            except:
                pass


def _parse_page_source(html: str) -> dict:
    """Parse financial data from page HTML"""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    
    tables = soup.find_all("table")
    st.write(f"📊 Found {len(tables)} tables")
    
    for table in tables:
        table_text = table.get_text().lower()
        if any(word in table_text for word in ["resultat", "inntekt", "eiendel", "driftsinntekt"]):
            st.write("✅ Found financial table")
            
            # Extract years
            years = []
            for th in table.find_all("th"):
                year_match = re.search(r"(202\d)", th.get_text())
                if year_match:
                    years.append(year_match.group(1))
            
            years = list(dict.fromkeys(years))
            st.write(f"📅 Years: {years}")
            
            # Parse rows
            for row in table.find_all("tr"):
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
                    
                    if "sum driftsinntekt" in label or "driftsinntekter" in label:
                        data[f"sum_driftsinnt_{year}"] = clean_value
                        st.write(f"  ✓ Revenue {year}: {clean_value}")
                    elif "driftsresultat" in label and "før" not in label:
                        data[f"driftsresultat_{year}"] = clean_value
                        st.write(f"  ✓ Operating result {year}: {clean_value}")
                    elif "resultat før skatt" in label or "ordinært resultat" in label:
                        data[f"ord_res_f_skatt_{year}"] = clean_value
                        st.write(f"  ✓ Result before tax {year}: {clean_value}")
                    elif "sum eiendeler" in label:
                        data[f"sum_eiendeler_{year}"] = clean_value
                        st.write(f"  ✓ Total assets {year}: {clean_value}")
            
            break
    
    return data
