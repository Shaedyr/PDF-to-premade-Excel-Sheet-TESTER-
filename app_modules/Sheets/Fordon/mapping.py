# app_modules/Sheets/Fordon/mapping.py
"""
SMART VEHICLE CATEGORIZATION - FIXED PATTERNS
- More flexible table pattern to catch all 19 cars
- Better unregistered machine pattern
- Cleans up extra text (like "ASA", "AS")
"""

import re
import streamlit as st


# Row ranges for each vehicle type
VEHICLE_ROWS = {
    "car": {"start": 3, "end": 22, "name": "Cars"},  # B3-B22 (20 slots)
    "trailer": {"start": 26, "end": 34, "name": "Trailers"},  # B26-B34 (9 slots)
    "moped": {"start": 38, "end": 46, "name": "Mopeds"},  # B38-B46 (9 slots)
    "tractor": {"start": 50, "end": 60, "name": "Tractors"},  # B50-B60 (11 slots)
    "boat": {"start": 64, "end": 72, "name": "Boats"},  # B64-B72 (9 slots)
}

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


# PATTERN LIBRARY
VEHICLE_PATTERNS = {
    "If_Skadeforsikring": {
        "name": "If Skadeforsikring",
        "pattern": r'([A-Z]{2}\d{5}),\s*(Varebil|Personbil|Lastebil|Moped|Traktor|Båt|Tilhenger),\s*([A-Z][A-Z\s]+?)(?:\s+(\d+)|$)',
        "extract_func": "extract_if_format",
        "priority": 1,
    },
    "Gjensidige_Unreg_Simple": {
        "name": "Gjensidige unregistered (simple)",
        "pattern": r'Uregistrert traktor og arb[.\s]*maskin[.\s]*-[.\s]*(Doosan|Hitachi|Caterpillar|Liebherr|Sennebogen|Komatsu|Volvo)\s+([0-9A-Z\s]+?)(?:-|Uregistrert|\n)',
        "extract_func": "extract_gjensidige_unreg_simple",
        "priority": 2,
    },
    "Gjensidige_Table_Flexible": {
        "name": "Gjensidige table (flexible)",
        "pattern": r'((?:[A-Z]+\s+)*?(?:VOLKSWAGEN|FORD|TOYOTA|MERCEDES-BENZ|MERCEDES|LAND ROVER|CITROEN|PEUGEOT|VOLVO|SCANIA|MAN)[A-Z\s\-()0-9]*?)\s+(\d{4})\s+([A-Z]{2}\s?\d{5})',
        "extract_func": "extract_gjensidige_table_flexible",
        "priority": 3,
    },
}


def categorize_vehicle(vehicle_info: dict) -> str:
    """Categorize vehicle by type."""
    vehicle_type = vehicle_info.get("vehicle_type", "").lower()
    make_model = vehicle_info.get("make_model_year", "").lower()
    
    # Explicit type from PDF
    if "tilhenger" in vehicle_type or "henger" in vehicle_type:
        return "trailer"
    elif "moped" in vehicle_type:
        return "moped"
    elif "traktor" in vehicle_type or "arbeidsmaskin" in vehicle_type:
        return "tractor"
    elif "båt" in vehicle_type or "boat" in vehicle_type:
        return "boat"
    elif any(x in vehicle_type for x in ["varebil", "personbil", "lastebil", "bil"]):
        return "car"
    
    # Check for machine brands (tractors)
    machine_brands = ["hitachi", "doosan", "caterpillar", "liebherr", "sennebogen", "komatsu"]
    if any(brand in make_model for brand in machine_brands):
        return "tractor"
    
    # Default to car
    return "car"


def extract_vehicles_from_pdf(pdf_text: str) -> dict:
    """Extract and categorize vehicles."""
    
    st.write("🔍 **FORDON: Smart extraction**")
    
    if not pdf_text:
        st.error("❌ No PDF text")
        return {}
    
    st.write(f"📄 PDF text: {len(pdf_text)} chars")
    
    if len(pdf_text) < 1000:
        st.error(f"⚠️ PDF text too short ({len(pdf_text)} chars)!")
        return {}
    
    st.write("---")
    
    all_vehicles = []
    
    # Try each pattern
    sorted_patterns = sorted(
        VEHICLE_PATTERNS.items(),
        key=lambda x: x[1]["priority"]
    )
    
    for pattern_id, pattern_config in sorted_patterns:
        pattern_name = pattern_config["name"]
        pattern_regex = pattern_config["pattern"]
        extract_func_name = pattern_config["extract_func"]
        
        st.write(f"  🔎 {pattern_name}")
        
        extract_func = globals().get(extract_func_name)
        if not extract_func:
            st.error(f"    ❌ Function not found: {extract_func_name}")
            continue
        
        try:
            extracted = extract_func(pdf_text, pattern_regex)
            
            if extracted:
                st.write(f"    ✅ {len(extracted)} vehicles")
                all_vehicles.extend(extracted)
            else:
                st.write(f"    ⊘ No matches")
        except Exception as e:
            st.error(f"    ❌ Error: {str(e)}")
    
    # Categorize
    st.write("---")
    st.write("📦 **Categorizing:**")
    
    categorized = {
        "car": [],
        "trailer": [],
        "moped": [],
        "tractor": [],
        "boat": [],
    }
    
    for vehicle in all_vehicles:
        category = categorize_vehicle(vehicle)
        categorized[category].append(vehicle)
    
    # Show summary
    for category, vehicles in categorized.items():
        if vehicles:
            name = VEHICLE_ROWS[category]["name"]
            st.write(f"  🚗 {name}: {len(vehicles)}")
            for v in vehicles[:3]:  # Show first 3
                st.write(f"    - {v['registration']} - {v['make_model_year']}")
            if len(vehicles) > 3:
                st.write(f"    ... and {len(vehicles)-3} more")
    
    total = sum(len(v) for v in categorized.values())
    st.write("---")
    st.success(f"✅ **TOTAL: {total} vehicles**")
    
    if total == 0:
        _show_debug_info(pdf_text)
    
    return categorized


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def extract_if_format(pdf_text: str, pattern: str) -> list:
    """Extract from If format."""
    vehicles = []
    matches = re.finditer(pattern, pdf_text, re.MULTILINE)
    
    for match in matches:
        reg_number = match.group(1).strip()
        vehicle_type = match.group(2).strip()
        make_partial = match.group(3).strip()
        
        # Look for continuation on next line
        pos = match.start()
        window = pdf_text[pos:pos+200]
        make_model = make_partial
        
        lines_after = window.split('\n')[1:3]
        for line in lines_after:
            line = line.strip()
            if line and line[0].isupper() and not re.match(r'[A-Z]{2}\d{5}', line):
                if not any(c.isdigit() for c in line[:10]):
                    make_model += " " + line.split()[0]
                    break
        
        year = _find_year_for_vehicle(pdf_text, reg_number)
        
        vehicle = {
            "registration": reg_number,
            "vehicle_type": vehicle_type,
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


def extract_gjensidige_unreg_simple(pdf_text: str, pattern: str) -> list:
    """Extract Gjensidige unregistered machines - SIMPLER pattern."""
    vehicles = []
    
    # Try the pattern
    matches = list(re.finditer(pattern, pdf_text, re.MULTILINE | re.DOTALL))
    
    if not matches:
        # Fallback: search for the text manually
        st.write("    🔍 Trying manual search for unregistered machines...")
        
        # Look for lines containing "Uregistrert traktor"
        lines = pdf_text.split('\n')
        for i, line in enumerate(lines):
            if 'Uregistrert traktor' in line or 'arbeidsmaskin' in line.lower():
                # Try to extract make/model from this line
                for brand in ['Doosan', 'Hitachi', 'Caterpillar', 'Liebherr', 'Sennebogen', 'Komatsu', 'Volvo']:
                    if brand in line:
                        # Extract model after brand
                        parts = line.split(brand)
                        if len(parts) > 1:
                            model_part = parts[1].strip()
                            # Extract model (letters, numbers, spaces until dash or newline)
                            model_match = re.match(r'([0-9A-Z\s]+?)(?:-|\n|Uregistrert)', model_part)
                            if model_match:
                                model = model_match.group(1).strip()
                                
                                # Look for year nearby
                                year = "2024"
                                year_match = re.search(r'\b(20\d{2})\b', line)
                                if year_match:
                                    year = year_match.group(1)
                                
                                vehicle = {
                                    "registration": "Uregistrert",
                                    "vehicle_type": "traktor",
                                    "make_model_year": f"{brand} {model} {year}",
                                    "insurance_sum": "",
                                    "coverage": "kasko",
                                    "leasing": "",
                                    "annual_mileage": "",
                                    "odometer": "",
                                    "bonus": "",
                                    "deductible": "",
                                }
                                vehicles.append(vehicle)
                                st.write(f"      Found: {brand} {model}")
        
        return vehicles
    
    # Normal pattern matching
    for match in matches:
        make = match.group(1).strip()
        model = match.group(2).strip()
        
        # Look for year nearby
        pos = match.start()
        window = pdf_text[max(0, pos-100):min(len(pdf_text), pos+400)]
        year_match = re.search(r'\b(20\d{2})\b', window)
        year = year_match.group(1) if year_match else "2024"
        
        vehicle = {
            "registration": "Uregistrert",
            "vehicle_type": "traktor",
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


def extract_gjensidige_table_flexible(pdf_text: str, pattern: str) -> list:
    """Extract from Gjensidige table - MORE FLEXIBLE."""
    vehicles = []
    matches = re.finditer(pattern, pdf_text, re.MULTILINE)
    
    for match in matches:
        make_model_raw = match.group(1).strip()
        year = match.group(2).strip()
        reg_number = match.group(3).strip().replace(" ", "")
        
        # Clean up make/model - remove company suffixes
        make_model = _clean_make_model(make_model_raw)
        
        vehicle = {
            "registration": reg_number,
            "vehicle_type": "bil",
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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _clean_make_model(text: str) -> str:
    """Clean up make/model text - remove company suffixes."""
    # Remove common suffixes that appear before the actual make
    text = re.sub(r'^(AS|ASA|E)\s+', '', text)  # Remove leading AS, ASA, E
    text = re.sub(r'\s+(AS|ASA)$', '', text)  # Remove trailing AS, ASA
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    return text.strip()


def _find_year_for_vehicle(pdf_text: str, reg_number: str) -> str:
    """Find year."""
    pattern = rf'{reg_number}.*?(?:Årsmodell|År|registrert):\s*(\d{{4}})'
    match = re.search(pattern, pdf_text, re.DOTALL)
    return match.group(1) if match else "2024"


def _extract_leasing(pdf_text: str, reg_number: str) -> str:
    """Extract leasing info."""
    if reg_number == "Uregistrert":
        return ""
    
    reg_pos = pdf_text.find(reg_number)
    if reg_pos == -1:
        return ""
    
    window = pdf_text[max(0, reg_pos-200):min(len(pdf_text), reg_pos+500)]
    
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
    
    return "Ja" if re.search(r'(leasing|tredjemannsinteresse)', window, re.I) else ""


def _show_debug_info(pdf_text: str):
    """Show debug info."""
    with st.expander("🔍 PDF text sample (2000-5000)"):
        st.code(pdf_text[2000:5000])
    
    with st.expander("🔍 PDF text sample (10000-13000)"):
        st.code(pdf_text[10000:13000])
    
    reg_patterns = re.findall(r'\b([A-Z]{2}\s?\d{5})\b', pdf_text)
    if reg_patterns:
        st.write("Found registration patterns:", list(set(reg_patterns[:20])))


# ============================================================================
# TRANSFORM FOR EXCEL
# ============================================================================

def transform_data(extracted: dict) -> dict:
    """Transform to Excel cells."""
    
    st.write("🔄 **FORDON: transform_data**")
    
    out = {}
    
    pdf_text = extracted.get("pdf_text", "")
    
    if not pdf_text:
        st.error("❌ No pdf_text!")
        return out
    
    categorized = extract_vehicles_from_pdf(pdf_text)
    
    if not categorized:
        return out
    
    st.write("---")
    st.write("📋 **Mapping to Excel:**")
    
    total_mapped = 0
    
    for category, vehicles in categorized.items():
        if not vehicles:
            continue
        
        row_config = VEHICLE_ROWS[category]
        start_row = row_config["start"]
        end_row = row_config["end"]
        name = row_config["name"]
        
        st.write(f"  📌 {name}: Rows {start_row}-{end_row}")
        
        for idx, vehicle in enumerate(vehicles):
            row_num = start_row + idx
            
            if row_num > end_row:
                st.warning(f"  ⚠️ Too many {name}!")
                break
            
            for field, column in VEHICLE_COLUMNS.items():
                cell_ref = f"{column}{row_num}"
                out[cell_ref] = vehicle.get(field, "")
            
            st.write(f"    Row {row_num}: {vehicle['registration']} - {vehicle['make_model_year']}")
            total_mapped += 1
    
    st.success(f"✅ Mapped {total_mapped} vehicles")
    
    return out


CELL_MAP = {}
