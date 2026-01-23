# app_modules/Sheets/Fordon/mapping.py
"""
Mapping for Fordon sheet - FIXED for If insurance format
where vehicle names are split across lines!
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
    """Extract vehicles from If insurance PDF format."""
    
    st.write("🔍 **FORDON: Extracting vehicles**")
    
    vehicles = []
    
    if not pdf_text:
        st.error("❌ No PDF text")
        return vehicles
    
    st.write(f"📄 PDF text: {len(pdf_text)} chars")
    
    # NEW PATTERN for If insurance format:
    # PR59518, Varebil, VOLKSWAGEN AMAROK
    # OR split across lines:
    # PR59518, Varebil, VOLKSWAGEN
    # TRANSPORTER
    
    # Pattern that handles BOTH formats
    pattern = r'(PR\d{5}|[A-Z]{2}\d{5}),\s*(?:Varebil|Personbil|Lastebil|Moped|Traktor|Båt),\s*([A-Z][A-Z\s]+?)(?:\s+(\d+)|$)'
    
    st.write("🔎 Using If insurance format pattern...")
    
    # First pass: Find all registration numbers with partial names
    matches = re.finditer(pattern, pdf_text, re.MULTILINE)
    
    for match in matches:
        reg_number = match.group(1).strip()
        make_partial = match.group(2).strip()
        
        st.write(f"  Found: {reg_number} - {make_partial}")
        
        # Now find the FULL make/model by looking at the next few lines
        # Get position of this match
        pos = match.start()
        
        # Get text around this registration (next 200 chars)
        window = pdf_text[pos:pos+200]
        
        # Extract the full vehicle name (may be split across lines)
        # Look for the make/model which continues until we hit a number or new line with registration
        make_model = make_partial
        
        # Try to find continuation on next line
        lines_after = window.split('\n')[1:3]  # Next 2 lines
        for line in lines_after:
            line = line.strip()
            # If line starts with uppercase word and no registration number, it's probably continuation
            if line and line[0].isupper() and not re.match(r'[A-Z]{2}\d{5}', line) and not any(c.isdigit() for c in line[:10]):
                make_model += " " + line.split()[0]  # Add first word from next line
                break
        
        st.write(f"    Full name: {make_model}")
        
        # Get year - look in detailed section later in PDF
        year = _find_year_for_vehicle(pdf_text, reg_number)
        
        vehicle = {
            "registration": reg_number,
            "make_model_year": f"{make_model} {year}",
            "insurance_sum": "",
            "coverage": "kasko",
            "leasing": _extract_leasing(pdf_text, reg_number),
            "annual_mileage": "16 000",
            "odometer": "",
            "bonus": "",
            "deductible": "8 000",
        }
        
        vehicles.append(vehicle)
    
    if vehicles:
        st.success(f"✅ Extracted {len(vehicles)} vehicles!")
        for i, v in enumerate(vehicles, 1):
            st.write(f"  {i}. {v['registration']} - {v['make_model_year']}")
    else:
        st.warning("⚠️ No vehicles found")
        
        # Debug info
        with st.expander("🔍 Vehicle section (2000-5000)"):
            st.code(pdf_text[2000:5000])
    
    return vehicles


def _find_year_for_vehicle(pdf_text: str, reg_number: str) -> str:
    """Find year for vehicle - usually in detailed section."""
    # Look for "Årsmodell: 2020" near the registration number
    pattern = rf'{reg_number}.*?Årsmodell:\s*(\d{{4}})'
    match = re.search(pattern, pdf_text, re.DOTALL)
    if match:
        return match.group(1)
    
    # Default to current year if not found
    return "2024"


def _extract_leasing(pdf_text: str, reg_number: str) -> str:
    """Extract leasing info."""
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return ""
    
    window = pdf_text[max(0, reg_pos-200):min(len(pdf_text), reg_pos+500)]
    
    if re.search(r'(leasing|tredjemannsinteresse)', window, re.IGNORECASE):
        # Try to find company name
        leasing_patterns = [
            r'(BRAGE FINANS)',
            r'(DNB FINANS)',
            r'(SANTANDER)',
            r'(NORDEA FINANS)',
        ]
        
        for pattern in leasing_patterns:
            match = re.search(pattern, window, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Ja"
    
    return ""


def transform_data(extracted: dict) -> dict:
    """Transform data for Fordon sheet."""
    
    st.write("🔄 **FORDON: transform_data**")
    
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
                    
            st.success(f"✅ Mapped {len(vehicles)} vehicles to Excel")
        else:
            st.warning("⚠️ No vehicles to map")
    else:
        st.error("❌ No pdf_text!")
    
    return out


CELL_MAP = {}
