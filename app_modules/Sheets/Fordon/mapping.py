# app_modules/Sheets/Fordon/mapping.py
"""
Mapping configuration for the Fordon (Vehicles) sheet.
UPDATED: Shows vehicle section of PDF for debugging
"""

import re
import streamlit as st


VEHICLE_START_ROW = 3

VEHICLE_COLUMNS = {
    "registration": "B",
    "make_model_year": "C",
    "insurance_sum": "D",
    "coverage": "E",
    "leasing": "F",
    "annual_mileage": "G",
    "odometer": "H",
    "bonus": "I",
    "deductible": "J",
}


def extract_vehicles_from_pdf(pdf_text: str) -> list:
    """Extract vehicle information from PDF text."""
    
    st.write("🔍 **FORDON: Extracting vehicles from PDF**")
    
    vehicles = []
    
    if not pdf_text:
        st.error("❌ No PDF text provided")
        return vehicles
    
    st.write(f"📄 PDF text length: {len(pdf_text)} characters")
    
    # PATTERN 1: If Skadeforsikring format
    pattern1 = r'([A-Z]{2}\d{5}),\s*(?:Varebil|Personbil|Lastebil),\s*([A-Z\s]+(?:[A-Z\s]+)?)\s+.*?Årsmodell:\s*(\d{4})'
    
    # PATTERN 2: Simple format
    pattern2 = r'\b([A-Z]{2}\d{5})\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+(\d{4})\b'
    
    # PATTERN 3: Table format
    pattern3 = r'([A-Z]{2}\d{5})\s*[|\t]+\s*([A-Z][A-Za-z\s]+?)\s*[|\t]+\s*(\d{4})'
    
    patterns = [
        ("If Skadeforsikring format", pattern1),
        ("Simple format", pattern2),
        ("Table format", pattern3),
    ]
    
    # Try each pattern
    for pattern_name, pattern in patterns:
        st.write(f"🔎 Trying pattern: {pattern_name}")
        
        matches = list(re.finditer(pattern, pdf_text, re.MULTILINE | re.DOTALL))
        
        if matches:
            st.success(f"✅ Found {len(matches)} vehicles using {pattern_name}")
            
            for idx, match in enumerate(matches, 1):
                reg_number = match.group(1).strip()
                make_model = match.group(2).strip()
                year = match.group(3).strip()
                
                st.write(f"  {idx}. {reg_number} - {make_model} {year}")
                
                vehicle = {
                    "registration": reg_number,
                    "make_model_year": f"{make_model} {year}",
                    "insurance_sum": "",
                    "coverage": _extract_coverage(pdf_text, reg_number),
                    "leasing": _extract_leasing(pdf_text, reg_number),
                    "annual_mileage": _extract_mileage(pdf_text, reg_number),
                    "odometer": "",
                    "bonus": "",
                    "deductible": _extract_deductible(pdf_text, reg_number),
                }
                
                vehicles.append(vehicle)
            
            break
    
    if not vehicles:
        st.warning("⚠️ No vehicles found with any pattern")
        st.info("💡 The PDF might use a different format")
        
        # SHOW MULTIPLE SECTIONS OF PDF - VEHICLE SECTION IS AROUND CHARS 2000-8000!
        st.write("---")
        st.write("📄 **PDF Text Samples:**")
        
        with st.expander("🔍 Beginning (0-2000) - Usually broker info"):
            st.code(pdf_text[:2000])
        
        with st.expander("🔍 ⭐ VEHICLE SECTION (2000-5000) - CHECK HERE!"):
            st.code(pdf_text[2000:5000])
        
        with st.expander("🔍 More vehicles (5000-8000)"):
            st.code(pdf_text[5000:8000])
        
        with st.expander("🔍 End section (8000-10000)"):
            st.code(pdf_text[8000:10000] if len(pdf_text) > 8000 else "Not enough text")
        
        # Show registration patterns found
        st.write("---")
        st.write("🔍 **Found these registration-like patterns:**")
        reg_patterns = re.findall(r'\b([A-Z]{2}\d{5})\b', pdf_text)
        if reg_patterns:
            for reg in set(reg_patterns[:10]):
                st.write(f"  - {reg}")
        else:
            st.write("  No standard registration numbers found")
    
    return vehicles


def _extract_coverage(pdf_text: str, reg_number: str) -> str:
    """Extract coverage type for a specific vehicle"""
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return "kasko"
    
    window = pdf_text[max(0, reg_pos-200):min(len(pdf_text), reg_pos+300)]
    
    coverage_keywords = {
        "kasko": ["kasko"],
        "ansvar": ["ansvar"],
        "delkasko": ["delkasko"],
    }
    
    for coverage_type, keywords in coverage_keywords.items():
        for keyword in keywords:
            if keyword.lower() in window.lower():
                return coverage_type
    
    return "kasko"


def _extract_leasing(pdf_text: str, reg_number: str) -> str:
    """Extract leasing company for a specific vehicle"""
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return ""
    
    window = pdf_text[max(0, reg_pos-200):min(len(pdf_text), reg_pos+300)]
    
    leasing_patterns = [
        r'(BRAGE FINANS AS)',
        r'(DNB FINANS)',
        r'(SANTANDER)',
        r'(NORDEA FINANS)',
        r'([A-Z\s]+ FINANS[A-Z\s]*)',
    ]
    
    for pattern in leasing_patterns:
        match = re.search(pattern, window, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    if re.search(r'(leasing|tredjemannsinteresse)', window, re.IGNORECASE):
        return "Ja"
    
    return ""


def _extract_mileage(pdf_text: str, reg_number: str) -> str:
    """Extract annual mileage for a specific vehicle"""
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return "16 000"
    
    window = pdf_text[max(0, reg_pos-300):min(len(pdf_text), reg_pos+400)]
    
    mileage_patterns = [
        r'(?:inntil|opp til|årlig|kjørelengde)[\s:]*(\d{1,3}[\s.]?\d{3})',
        r'(\d{1,3}[\s.]?\d{3})[\s]*km',
    ]
    
    for pattern in mileage_patterns:
        match = re.search(pattern, window, re.IGNORECASE)
        if match:
            mileage = match.group(1).replace(".", " ").strip()
            return mileage
    
    return "16 000"


def _extract_deductible(pdf_text: str, reg_number: str) -> str:
    """Extract deductible (egenandel) for a specific vehicle"""
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return "8 000"
    
    window = pdf_text[max(0, reg_pos-300):min(len(pdf_text), reg_pos+400)]
    
    deductible_patterns = [
        r'(?:egenandel|selvrisiko)[\s:]*(\d{1,3}[\s.]?\d{3})',
        r'(\d{1,3}[\s.]?\d{3})[\s]*kr.*egenandel',
    ]
    
    for pattern in deductible_patterns:
        match = re.search(pattern, window, re.IGNORECASE)
        if match:
            deductible = match.group(1).replace(".", " ").strip()
            return deductible
    
    return "8 000"


def transform_data(extracted: dict) -> dict:
    """Transform raw extracted data into Fordon sheet format."""
    
    st.write("🔄 **FORDON: transform_data called**")
    
    out = {}
    
    pdf_text = extracted.get("pdf_text", "")
    
    if pdf_text:
        st.write("✅ PDF text found")
        vehicles = extract_vehicles_from_pdf(pdf_text)
        
        if vehicles:
            for idx, vehicle in enumerate(vehicles):
                row_num = VEHICLE_START_ROW + idx
                
                for field, column in VEHICLE_COLUMNS.items():
                    cell_ref = f"{column}{row_num}"
                    out[cell_ref] = vehicle.get(field, "")
                    
            st.success(f"✅ Created mappings for {len(vehicles)} vehicles")
        else:
            st.warning("⚠️ No vehicles extracted from PDF")
    else:
        st.error("❌ No pdf_text in extracted data")
    
    return out


CELL_MAP = {}
