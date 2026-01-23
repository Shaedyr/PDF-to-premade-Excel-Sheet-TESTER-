# app_modules/Sheets/Fordon/mapping.py
"""
FLEXIBLE MULTI-PATTERN VEHICLE EXTRACTION
Handles multiple insurance company formats automatically
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


# PATTERN LIBRARY - Add new patterns here as you encounter them!
VEHICLE_PATTERNS = {
    "If_Skadeforsikring": {
        "name": "If Skadeforsikring (split lines)",
        "pattern": r'([A-Z]{2}\d{5}),\s*(?:Varebil|Personbil|Lastebil|Moped|Traktor|Båt),\s*([A-Z][A-Z\s]+?)(?:\s+(\d+)|$)',
        "extract_func": "extract_if_format",
        "priority": 1,
    },
    "Gjensidige_Table": {
        "name": "Gjensidige (table format)",
        "pattern": r'([A-Z\s\-]+(?:VOLKSWAGEN|FORD|TOYOTA|MERCEDES|LAND ROVER|CITROEN|PEUGEOT|VOLVO|SCANIA|MAN|DOOSAN|HITACHI|CATERPILLAR|LIEBHERR|SENNEBOGEN)[A-Z\s\-]*)\s+(\d{4})\s+([A-Z]{2}\s?\d{5})',
        "extract_func": "extract_gjensidige_table",
        "priority": 2,
    },
    "Gjensidige_Unreg": {
        "name": "Gjensidige (unregistered machines)",
        "pattern": r'(Hitachi|Doosan|Caterpillar|Liebherr|Sennebogen|Komatsu|Volvo)\s+([0-9A-Z\s]+?)(?:Uregistrert|-).*?(?:Første gang registrert|registrert):\s*(\d{4})',
        "extract_func": "extract_gjensidige_unreg",
        "priority": 3,
    },
    "Simple": {
        "name": "Simple format (reg make year)",
        "pattern": r'\b([A-Z]{2}\d{5})\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+(\d{4})\b',
        "extract_func": "extract_simple",
        "priority": 4,
    },
}


def extract_vehicles_from_pdf(pdf_text: str) -> list:
    """
    FLEXIBLE extraction - tries multiple patterns automatically.
    """
    
    st.write("🔍 **FORDON: Flexible vehicle extraction**")
    
    vehicles = []
    
    if not pdf_text:
        st.error("❌ No PDF text")
        return vehicles
    
    st.write(f"📄 PDF text: {len(pdf_text)} chars")
    st.write("---")
    st.write("🎯 **Trying patterns in priority order:**")
    
    # Sort patterns by priority
    sorted_patterns = sorted(
        VEHICLE_PATTERNS.items(),
        key=lambda x: x[1]["priority"]
    )
    
    # Try each pattern until we find vehicles
    for pattern_id, pattern_config in sorted_patterns:
        pattern_name = pattern_config["name"]
        pattern_regex = pattern_config["pattern"]
        extract_func_name = pattern_config["extract_func"]
        
        st.write(f"  🔎 Pattern {pattern_config['priority']}: {pattern_name}")
        
        # Get the extraction function
        extract_func = globals().get(extract_func_name)
        if not extract_func:
            st.error(f"    ❌ Function '{extract_func_name}' not found!")
            continue
        
        # Try to extract vehicles with this pattern
        try:
            extracted = extract_func(pdf_text, pattern_regex)
            
            if extracted:
                st.success(f"  ✅ **Found {len(extracted)} vehicles using '{pattern_name}'!**")
                vehicles = extracted
                break  # Found vehicles, stop trying patterns
            else:
                st.write(f"    ⊘ No matches")
        except Exception as e:
            st.error(f"    ❌ Error: {e}")
    
    # Show results
    st.write("---")
    if vehicles:
        st.success(f"✅ **TOTAL: {len(vehicles)} vehicles extracted**")
        for i, v in enumerate(vehicles, 1):
            st.write(f"  {i}. {v['registration']} - {v['make_model_year']}")
    else:
        st.warning("⚠️ **No vehicles found with any pattern**")
        _show_debug_info(pdf_text)
    
    return vehicles


# ============================================================================
# EXTRACTION FUNCTIONS FOR EACH PATTERN
# ============================================================================

def extract_if_format(pdf_text: str, pattern: str) -> list:
    """
    Extract vehicles from If Skadeforsikring format.
    Handles split lines: 
      PR59522, Varebil, VOLKSWAGEN
      TRANSPORTER
    """
    vehicles = []
    matches = re.finditer(pattern, pdf_text, re.MULTILINE)
    
    for match in matches:
        reg_number = match.group(1).strip()
        make_partial = match.group(2).strip()
        
        # Get position and look at next lines for continuation
        pos = match.start()
        window = pdf_text[pos:pos+200]
        
        make_model = make_partial
        
        # Check if model name continues on next line
        lines_after = window.split('\n')[1:3]
        for line in lines_after:
            line = line.strip()
            # If line starts with uppercase word and no numbers/registration
            if line and line[0].isupper() and not re.match(r'[A-Z]{2}\d{5}', line):
                if not any(c.isdigit() for c in line[:10]):
                    # This is probably the continuation
                    make_model += " " + line.split()[0]
                    break
        
        # Find year from detailed section
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
    
    return vehicles


def extract_gjensidige_table(pdf_text: str, pattern: str) -> list:
    """
    Extract vehicles from Gjensidige table format.
    Format: VOLKSWAGEN TRANSPORTER 2020 BU21895
    """
    vehicles = []
    matches = re.finditer(pattern, pdf_text, re.MULTILINE)
    
    for match in matches:
        make_model = match.group(1).strip()
        year = match.group(2).strip()
        reg_number = match.group(3).strip().replace(" ", "")  # Remove spaces
        
        vehicle = {
            "registration": reg_number,
            "make_model_year": f"{make_model} {year}",
            "insurance_sum": "",
            "coverage": "kasko",
            "leasing": _extract_leasing(pdf_text, reg_number),
            "annual_mileage": "16 000",
            "odometer": "",
            "bonus": "",
            "deductible": "",
        }
        
        vehicles.append(vehicle)
    
    return vehicles


def extract_gjensidige_unreg(pdf_text: str, pattern: str) -> list:
    """
    Extract unregistered machines from Gjensidige.
    Format: Hitachi 300 Uregistrert. - Første gang registrert: 2023
    """
    vehicles = []
    matches = re.finditer(pattern, pdf_text, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        make = match.group(1).strip()
        model = match.group(2).strip()
        year = match.group(3).strip()
        
        vehicle = {
            "registration": "Uregistrert",
            "make_model_year": f"{make} {model} {year}",
            "insurance_sum": "",
            "coverage": "kasko",
            "leasing": "",
            "annual_mileage": "",
            "odometer": "",
            "bonus": "",
            "deductible": "",
        }
        
        vehicles.append(vehicle)
    
    return vehicles


def extract_simple(pdf_text: str, pattern: str) -> list:
    """
    Extract vehicles from simple format.
    Format: AB12345 TOYOTA HILUX 2020
    """
    vehicles = []
    matches = re.finditer(pattern, pdf_text, re.MULTILINE)
    
    for match in matches:
        reg_number = match.group(1).strip()
        make_model = match.group(2).strip()
        year = match.group(3).strip()
        
        vehicle = {
            "registration": reg_number,
            "make_model_year": f"{make_model} {year}",
            "insurance_sum": "",
            "coverage": "kasko",
            "leasing": "",
            "annual_mileage": "16 000",
            "odometer": "",
            "bonus": "",
            "deductible": "8 000",
        }
        
        vehicles.append(vehicle)
    
    return vehicles


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _find_year_for_vehicle(pdf_text: str, reg_number: str) -> str:
    """Find year for vehicle in detailed section."""
    pattern = rf'{reg_number}.*?(?:Årsmodell|År|registrert):\s*(\d{{4}})'
    match = re.search(pattern, pdf_text, re.DOTALL)
    if match:
        return match.group(1)
    return "2024"


def _extract_leasing(pdf_text: str, reg_number: str) -> str:
    """Extract leasing info near registration number."""
    if reg_number == "Uregistrert":
        return ""
    
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return ""
    
    window = pdf_text[max(0, reg_pos-200):min(len(pdf_text), reg_pos+500)]
    
    # Look for leasing companies
    leasing_companies = [
        "Sparebank 1",
        "Nordea Finans",
        "Santander",
        "DNB Finans",
        "BRAGE FINANS",
    ]
    
    for company in leasing_companies:
        if company in window:
            return company
    
    if re.search(r'(leasing|tredjemannsinteresse)', window, re.IGNORECASE):
        return "Ja"
    
    return ""


def _show_debug_info(pdf_text: str):
    """Show debug information when no vehicles found."""
    st.write("💡 **Debug Information:**")
    
    # Show PDF sections
    with st.expander("🔍 Beginning (0-2000)"):
        st.code(pdf_text[:2000])
    
    with st.expander("🔍 ⭐ Vehicle section (2000-5000)"):
        st.code(pdf_text[2000:5000])
    
    with st.expander("🔍 More content (5000-8000)"):
        st.code(pdf_text[5000:8000])
    
    # Show found registration patterns
    st.write("🔍 **Registration-like patterns found:**")
    reg_patterns = re.findall(r'\b([A-Z]{2}\s?\d{5})\b', pdf_text)
    if reg_patterns:
        unique_regs = list(set(reg_patterns[:20]))
        for reg in unique_regs:
            st.write(f"  - {reg}")
    else:
        st.write("  No standard registration numbers found")


# ============================================================================
# TRANSFORM DATA FOR EXCEL
# ============================================================================

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
