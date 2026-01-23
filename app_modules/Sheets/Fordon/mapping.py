# app_modules/Sheets/Fordon/mapping.py
"""
Mapping configuration for the Fordon (Vehicles) sheet.
Extracts vehicle information from insurance PDFs.
FLEXIBLE VERSION - handles multiple PDF formats
"""

import re
import streamlit as st


# This sheet uses row-based mapping (one row per vehicle)
# Each vehicle becomes a new row starting from row 3
VEHICLE_START_ROW = 3

# Column mapping for vehicle data
VEHICLE_COLUMNS = {
    "registration": "B",      # Kjennemerke/Type (Registration number)
    "make_model_year": "C",   # Fabrikat/årsmodell/Type
    "insurance_sum": "D",     # Forsikringssum (kr)
    "coverage": "E",          # Dekning
    "leasing": "F",           # Leasing
    "annual_mileage": "G",    # Årlig kjørelengde
    "odometer": "H",          # Kilometerstand (dato)
    "bonus": "I",             # Bonus
    "deductible": "J",        # Egenandel
}


def extract_vehicles_from_pdf(pdf_text: str) -> list:
    """
    Extract vehicle information from PDF text.
    Tries multiple patterns to handle different PDF formats.
    Returns a list of vehicle dictionaries.
    """
    st.write("🔍 **FORDON: Extracting vehicles from PDF**")
    
    vehicles = []
    
    if not pdf_text:
        st.error("❌ No PDF text provided")
        return vehicles
    
    st.write(f"📄 PDF text length: {len(pdf_text)} characters")
    
    # Try multiple patterns to handle different insurance companies
    
    # PATTERN 1: If Skadeforsikring format
    # Example: "PR59518, Varebil, VOLKSWAGEN AMAROK ... Årsmodell: 2020"
    pattern1 = r'([A-Z]{2}\d{5}),\s*(?:Varebil|Personbil|Lastebil),\s*([A-Z\s]+(?:[A-Z\s]+)?)\s+.*?Årsmodell:\s*(\d{4})'
    
    # PATTERN 2: Simple registration + make/model format
    # Example: "AB12345 TOYOTA HILUX 2020"
    pattern2 = r'\b([A-Z]{2}\d{5})\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+(\d{4})\b'
    
    # PATTERN 3: Table format with columns
    # Example: "AB12345 | TOYOTA HILUX | 2020"
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
            
            break  # Found vehicles, stop trying patterns
    
    if not vehicles:
        st.warning("⚠️ No vehicles found with any pattern")
        st.info("💡 The PDF might use a different format")
        
        # Show sample of PDF for debugging
        with st.expander("🔍 View PDF text sample (first 2000 chars)"):
            st.code(pdf_text[:2000])
        
        # Show all registration-like patterns found
        st.write("🔍 Found these registration-like patterns:")
        reg_patterns = re.findall(r'\b([A-Z]{2}\d{5})\b', pdf_text)
        if reg_patterns:
            for reg in set(reg_patterns[:10]):  # Show first 10 unique
                st.write(f"  - {reg}")
        else:
            st.write("  No standard registration numbers found")
    
    return vehicles


def _extract_coverage(pdf_text: str, reg_number: str) -> str:
    """Extract coverage type for a specific vehicle"""
    # Look for coverage keywords near the registration number
    # Search in a 500 char window around the reg number
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return "kasko"  # Default
    
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
    
    return "kasko"  # Default


def _extract_leasing(pdf_text: str, reg_number: str) -> str:
    """Extract leasing company for a specific vehicle"""
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return ""
    
    window = pdf_text[max(0, reg_pos-200):min(len(pdf_text), reg_pos+300)]
    
    # Look for common leasing companies
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
    
    # Check for generic "leasing" or "Tredjemannsinteresse"
    if re.search(r'(leasing|tredjemannsinteresse)', window, re.IGNORECASE):
        return "Ja"
    
    return ""


def _extract_mileage(pdf_text: str, reg_number: str) -> str:
    """Extract annual mileage for a specific vehicle"""
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return "16 000"  # Default
    
    window = pdf_text[max(0, reg_pos-300):min(len(pdf_text), reg_pos+400)]
    
    # Look for mileage patterns
    mileage_patterns = [
        r'(?:inntil|opp til|årlig|kjørelengde)[\s:]*(\d{1,3}[\s.]?\d{3})',
        r'(\d{1,3}[\s.]?\d{3})[\s]*km',
    ]
    
    for pattern in mileage_patterns:
        match = re.search(pattern, window, re.IGNORECASE)
        if match:
            mileage = match.group(1).replace(".", " ").strip()
            return mileage
    
    return "16 000"  # Default


def _extract_deductible(pdf_text: str, reg_number: str) -> str:
    """Extract deductible (egenandel) for a specific vehicle"""
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return "8 000"  # Default
    
    window = pdf_text[max(0, reg_pos-300):min(len(pdf_text), reg_pos+400)]
    
    # Look for deductible patterns
    deductible_patterns = [
        r'(?:egenandel|selvrisiko)[\s:]*(\d{1,3}[\s.]?\d{3})',
        r'(\d{1,3}[\s.]?\d{3})[\s]*kr.*egenandel',
    ]
    
    for pattern in deductible_patterns:
        match = re.search(pattern, window, re.IGNORECASE)
        if match:
            deductible = match.group(1).replace(".", " ").strip()
            return deductible
    
    return "8 000"  # Default


def transform_data(extracted: dict) -> dict:
    """
    Transform raw extracted data into Fordon sheet format.
    
    Args:
        extracted: Raw data dictionary (includes pdf_text if available)
        
    Returns:
        Dictionary with vehicle data formatted for Excel
    """
    st.write("🔄 **FORDON: transform_data called**")
    
    out = {}
    
    # Check if we have PDF text to parse
    pdf_text = extracted.get("pdf_text", "")
    
    if pdf_text:
        st.write("✅ PDF text found")
        vehicles = extract_vehicles_from_pdf(pdf_text)
        
        if vehicles:
            # Map each vehicle to its row
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
        st.info("Make sure pdf_parser.py includes 'pdf_text' in output")
    
    return out


# Empty CELL_MAP - we use dynamic mapping
CELL_MAP = {}
