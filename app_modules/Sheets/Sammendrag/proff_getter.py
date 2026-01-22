# app_modules/Sheets/Sammendrag/proff_getter_SELENIUM.py
"""
Selenium-based Proff.no scraper - handles JavaScript
Requires: selenium, webdriver-manager
"""

import re
import time
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
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


@lru_cache(maxsize=1024)
def fetch_proff_info(org_number: str) -> dict:
    """
    Fetch financial data from Proff.no using Selenium (handles JavaScript)
    """
    st.write("=" * 50)
    st.write("🚀 FETCHING FROM PROFF.NO WITH SELENIUM")
    st.write("=" * 50)
    
    if not SELENIUM_AVAILABLE:
        st.error("❌ Selenium not installed!")
        st.info("""
        To use automated data fetching, install Selenium:
        
        ```
        pip install selenium webdriver-manager
        ```
        
        Then restart the app.
        """)
        return {}
    
    if not org_number or not org_number.isdigit():
        st.error("❌ Invalid org number")
        return {}
    
    st.write(f"🔍 Searching for org: {org_number}")
    
    driver = None
    try:
        # Set up Chrome in headless mode
        st.write("🌐 Setting up browser...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run without opening window
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Initialize driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        st.write("✅ Browser ready")
        
        # Go to Proff.no search
        search_url = f"https://www.proff.no/bransjesøk?q={org_number}"
        st.write(f"📄 Loading: {search_url}")
        driver.get(search_url)
        
        # Wait for search results to load (JavaScript)
        st.write("⏳ Waiting for search results...")
        time.sleep(3)  # Give JavaScript time to load
        
        # Look for company link
        st.write("🔎 Looking for company link...")
        try:
            # Try to find the first company result link
            company_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/selskap/']"))
            )
            
            company_url = company_link.get_attribute("href")
            st.success(f"✅ Found company: {company_url}")
            
            # Click the link
            st.write("🖱️ Clicking company link...")
            driver.get(company_url)
            
            # Wait for page to load
            time.sleep(3)
            
            st.write("📊 Parsing financial data...")
            
            # Get page source
            page_source = driver.page_source
            
            # Parse financial data from the page
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
            st.error(f"❌ Could not find company link: {e}")
            
            # Show what's on the page
            with st.expander("🔍 DEBUG: Page source sample"):
                st.code(driver.page_source[:2000])
            
            return {}
        
    except Exception as e:
        st.error(f"❌ Selenium error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return {}
        
    finally:
        # Always close the browser
        if driver:
            driver.quit()
            st.write("🔒 Browser closed")


def _parse_page_source(html: str) -> dict:
    """
    Parse financial data from Proff.no page HTML
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    
    # Find tables
    tables = soup.find_all("table")
    st.write(f"📊 Found {len(tables)} tables")
    
    # Look for financial table
    for table in tables:
        table_text = table.get_text().lower()
        if any(word in table_text for word in ["resultat", "inntekt", "eiendel", "driftsinntekt"]):
            st.write("✅ Found financial table")
            
            # Extract years from headers
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
            
            break  # Found financial table, no need to check others
    
    return data
