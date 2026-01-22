# app_modules/Sheets/Sammendrag/brreg_financial_getter.py
"""
Fetch financial data from BRREG's Regnskapsregisteret (Accounting Register)
Official API - no scraping needed!
"""

import requests
import streamlit as st
from functools import lru_cache

BRREG_ACCOUNTING_API = "https://data.brreg.no/regnskapsregisteret/regnskap"

@lru_cache(maxsize=1024)
def fetch_brreg_financial_data(org_number: str) -> dict:
    """
    Fetch financial data from BRREG's Accounting Register.
    
    Returns revenue, operating result, result before tax, and total assets
    for the most recent years available.
    """
    st.write("=" * 50)
    st.write("🚀 FETCHING FINANCIAL DATA FROM BRREG")
    st.write("=" * 50)
    
    if not org_number or not org_number.isdigit():
        st.error("❌ Invalid org number")
        return {}
    
    st.write(f"🔍 Searching for financial statements for org: {org_number}")
    
    # Fetch financial statements
    params = {
        "organisasjonsnummer": org_number,
        "regnskapstype": "SELSKAP",  # Company accounts
    }
    
    try:
        st.write(f"🌐 Fetching from BRREG API...")
        response = requests.get(BRREG_ACCOUNTING_API, params=params, timeout=10)
        st.write(f"📊 Status: {response.status_code}")
        
        if response.status_code != 200:
            st.error(f"❌ BRREG API error: {response.status_code}")
            return {}
        
        st.success("✅ Success! Got financial data from BRREG")
        
        data = response.json()
        
        # Check if we got any results
        if not data or "_embedded" not in data or "regnskap" not in data["_embedded"]:
            st.warning("⚠️ No financial statements found for this company")
            return {}
        
        statements = data["_embedded"]["regnskap"]
        st.write(f"📊 Found {len(statements)} financial statements")
        
        # Process statements and extract financial data
        financial_data = {}
        
        # Sort by year (most recent first)
        statements = sorted(statements, key=lambda x: x.get("regnskapperiode", {}).get("fraDato", ""), reverse=True)
        
        for statement in statements[:3]:  # Get last 3 years
            year = statement.get("regnskapperiode", {}).get("fraDato", "")[:4]  # Extract year
            
            if not year or int(year) < 2020:  # Only recent years
                continue
            
            st.write(f"📅 Processing year: {year}")
            
            # Get the result lines (resultatregnskapslinjer)
            result_lines = statement.get("resultatregnskapslinjer", {})
            
            # Extract the data we need
            for line in result_lines:
                label = line.get("linje", "").lower()
                value = line.get("belop", 0)
                
                # Revenue (Driftsinntekter)
                if "sum driftsinntekter" in label or label == "driftsinntekter":
                    financial_data[f"sum_driftsinnt_{year}"] = str(value)
                    st.write(f"  ✓ Revenue {year}: {value}")
                
                # Operating result (Driftsresultat)
                elif "driftsresultat" in label:
                    financial_data[f"driftsresultat_{year}"] = str(value)
                    st.write(f"  ✓ Operating result {year}: {value}")
                
                # Result before tax (Ordinært resultat før skattekostnad)
                elif "ordinært resultat før skatt" in label or "resultat før skatt" in label:
                    financial_data[f"ord_res_f_skatt_{year}"] = str(value)
                    st.write(f"  ✓ Result before tax {year}: {value}")
            
            # Get balance sheet data (balanselinjer)
            balance_lines = statement.get("balanselinjer", {})
            
            for line in balance_lines:
                label = line.get("linje", "").lower()
                value = line.get("belop", 0)
                
                # Total assets (Sum eiendeler)
                if "sum eiendeler" in label:
                    financial_data[f"sum_eiendeler_{year}"] = str(value)
                    st.write(f"  ✓ Total assets {year}: {value}")
        
        st.write("=" * 50)
        st.write(f"✅ DONE! Fetched {len(financial_data)} financial fields from BRREG")
        st.write("=" * 50)
        
        if financial_data:
            st.json(financial_data)
        else:
            st.warning("⚠️ No financial data could be extracted")
        
        return financial_data
        
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Network error: {e}")
        return {}
    
    except Exception as e:
        st.error(f"❌ Error processing financial data: {e}")
        import traceback
        st.code(traceback.format_exc())
        return {}


# For backwards compatibility, keep the same function name
def fetch_proff_info(org_number: str) -> dict:
    """
    Fetch financial data - now using BRREG instead of Proff.no
    """
    return fetch_brreg_financial_data(org_number)
