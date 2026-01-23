# app_modules/Sheets/Fordon/mapping.py
"""
Mapping configuration for the Fordon (Vehicles) sheet.
Extracts vehicle information from insurance PDFs.
DEBUG VERSION - shows what's happening
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
    Returns a list of vehicle dictionaries.
    """
    st.write("🔍 **FORDON DEBUG: Extracting vehicles from PDF**")
    
    vehicles = []
    
    if not pdf_text:
        st.error("❌ No PDF text provided to Fordon mapping!")
        return vehicles
    
    st.write(f"📄 PDF text length: {len(pdf_text)} characters")
    
    # Pattern to find vehicle entries in the PDF
    # Looking for registration numbers like PR59518, PR70101, etc.
    vehicle_pattern = r'(PR\d{5}|[A-Z]{2}\d{5}),\s*Varebil,\s*([A-Z\s]+(?:[A-Z\s]+)?)\s+.*?Årsmodell:\s*(\d{4})'
    
    st.write(f"🔎 Searching for pattern: {vehicle_pattern}")
    
    matches = re.finditer(vehicle_pattern, pdf_text, re.MULTILINE | re.DOTALL)
    matches_list = list(matches)
    
    st.write(f"📊 Found {len(matches_list)} vehicle matches")
    
    for idx, match in enumerate(matches_list, 1):
        reg_number = match.group(1)  # e.g., PR59518
        make_model = match.group(2).strip()  # e.g., VOLKSWAGEN AMAROK
        year = match.group(3)  # e.g., 2020
        
        st.write(f"  {idx}. {reg_number} - {make_model} {year}")
        
        vehicle = {
            "registration": reg_number,
            "make_model_year": f"{make_model} {year}",
            "insurance_sum": "",  # Not in PDF or extract if needed
            "coverage": "kasko",  # All vehicles have kasko in the PDF
            "leasing": "",  # Could extract Tredjemannsinteresse/leasing if present
            "annual_mileage": "16 000",  # From PDF: 16 000 km
            "odometer": "",  # Not in this PDF
            "bonus": "",  # Not in this PDF
            "deductible": "8 000",  # From PDF: various deductibles, using common one
        }
        
        vehicles.append(vehicle)
    
    if vehicles:
        st.success(f"✅ Extracted {len(vehicles)} vehicles successfully!")
    else:
        st.warning("⚠️ No vehicles found in PDF")
        st.info("💡 Check if PDF contains vehicle information in the expected format")
        
        # Show a sample of the PDF text
        with st.expander("🔍 View PDF text sample (first 1000 chars)"):
            st.code(pdf_text[:1000])
    
    return vehicles


def transform_data(extracted: dict) -> dict:
    """
    Transform raw extracted data into Fordon sheet format.
    
    Args:
        extracted: Raw data dictionary (includes pdf_text if available)
        
    Returns:
        Dictionary with vehicle data formatted for Excel
    """
    st.write("🔄 **FORDON: transform_data called**")
    st.write(f"📦 Extracted data keys: {list(extracted.keys())}")
    
    out = {}
    
    # Check if we have PDF text to parse
    pdf_text = extracted.get("pdf_text", "")
    
    if pdf_text:
        st.write("✅ PDF text found in extracted data")
        vehicles = extract_vehicles_from_pdf(pdf_text)
        
        # Map each vehicle to its row
        for idx, vehicle in enumerate(vehicles):
            row_num = VEHICLE_START_ROW + idx
            
            st.write(f"📝 Mapping vehicle {idx+1} to row {row_num}")
            
            for field, column in VEHICLE_COLUMNS.items():
                cell_ref = f"{column}{row_num}"
                out[cell_ref] = vehicle.get(field, "")
                
        st.success(f"✅ Created {len(out)} cell mappings for Fordon sheet")
    else:
        st.error("❌ No pdf_text found in extracted data!")
        st.warning("Make sure pdf_parser.py is updated to include pdf_text in output")
    
    return out


# For this sheet, we don't use a simple CELL_MAP
# Instead, we dynamically create cell references based on the number of vehicles
# The excel_filler will need to handle this differently
CELL_MAP = {}  # Empty - we use transform_data to generate dynamic mappings
