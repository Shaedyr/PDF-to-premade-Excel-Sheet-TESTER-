# app_modules/Sheets/Fordon/mapping.py
"""
SUPER FLEXIBLE VEHICLE EXTRACTION
Works with If + Gjensidige + any OCR quality
"""

import re
import streamlit as st


VEHICLE_ROWS = {
    "car": {"start": 3, "end": 22, "name": "Cars"},
    "trailer": {"start": 26, "end": 34, "name": "Trailers"},
    "moped": {"start": 38, "end": 46, "name": "Mopeds"},
    "tractor": {"start": 50, "end": 60, "name": "Tractors"},
    "boat": {"start": 64, "end": 72, "name": "Boats"},
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


# MACHINE BRANDS for tractors
MACHINE_BRANDS = ["Doosan", "Hitachi", "Caterpillar", "Liebherr", "Sennebogen", "Komatsu", "Volvo", "JCB", "Bobcat"]

# CAR BRANDS
CAR_BRANDS = ["VOLKSWAGEN", "FORD", "TOYOTA", "MERCEDES-BENZ", "MERCEDES", "LAND ROVER", "CITROEN", "PEUGEOT", "VOLVO", "SCANIA", "MAN", "BMW", "AUDI"]


def extract_vehicles_from_pdf(pdf_text: str) -> dict:
    """Extract and categorize vehicles."""
    
    st.write("🔍 **FORDON: Super flexible extraction**")
    
    if not pdf_text or len(pdf_text) < 1000:
        st.error("❌ PDF text too short!")
        return {}
    
    st.write(f"📄 PDF text: {len(pdf_text)} chars")
    st.write("---")
    
    all_vehicles = []
    
    # STRATEGY 1: If Skadeforsikring format
    st.write("  🔎 If Skadeforsikring format")
    if_vehicles = _extract_if_format(pdf_text)
    if if_vehicles:
        st.write(f"    ✅ {len(if_vehicles)} vehicles")
        all_vehicles.extend(if_vehicles)
    else:
        st.write("    ⊘ No matches")
    
    # STRATEGY 2: Find tractors by brand (works even with bad OCR)
    st.write("  🔎 Tractors (by brand search)")
    tractors = _extract_tractors_by_brand(pdf_text)
    if tractors:
        st.write(f"    ✅ {len(tractors)} tractors")
        all_vehicles.extend(tractors)
    else:
        st.write("    ⊘ No tractors")
    
    # STRATEGY 3: Gjensidige table - ALL registration numbers
    st.write("  🔎 Gjensidige table (all reg numbers)")
    table_vehicles = _extract_all_registrations(pdf_text)
    if table_vehicles:
        st.write(f"    ✅ {len(table_vehicles)} vehicles")
        all_vehicles.extend(table_vehicles)
    else:
        st.write("    ⊘ No table vehicles")
    
    # Categorize
    categorized = _categorize_all(all_vehicles)
    
    st.write("---")
    st.write("📦 **Categorized:**")
    for category, vehicles in categorized.items():
        if vehicles:
            st.write(f"  🚗 {VEHICLE_ROWS[category]['name']}: {len(vehicles)}")
            for v in vehicles[:3]:
                st.write(f"    - {v['registration']} - {v['make_model_year']}")
            if len(vehicles) > 3:
                st.write(f"    ... +{len(vehicles)-3} more")
    
    total = sum(len(v) for v in categorized.values())
    st.success(f"✅ **TOTAL: {total} vehicles**")
    
    return categorized


def _extract_if_format(text: str) -> list:
    """Extract If Skadeforsikring format."""
    vehicles = []
    pattern = r'([A-Z]{2}\d{5}),\s*(Varebil|Personbil|Lastebil|Moped|Traktor|Båt|Tilhenger),\s*([A-Z][A-Z\s]+?)(?:\s+(\d+)|$)'
    
    for match in re.finditer(pattern, text, re.MULTILINE):
        reg = match.group(1).strip()
        vtype = match.group(2).strip()
        make = match.group(3).strip()
        
        # Look for continuation on next line
        pos = match.start()
        window = text[pos:pos+200]
        lines_after = window.split('\n')[1:3]
        for line in lines_after:
            line = line.strip()
            if line and line[0].isupper() and not re.match(r'[A-Z]{2}\d{5}', line):
                if not any(c.isdigit() for c in line[:10]):
                    make += " " + line.split()[0]
                    break
        
        year = _find_year(text, reg)
        
        vehicles.append({
            "registration": reg,
            "vehicle_type": vtype,
            "make_model_year": f"{make} {year}",
            "coverage": "kasko",
            "leasing": _find_leasing(text, reg),
            "annual_mileage": "16 000",
            "deductible": "8 000",
            "insurance_sum": "", "odometer": "", "bonus": "",
        })
    
    return vehicles


def _extract_tractors_by_brand(text: str) -> list:
    """Find tractors by searching for machine brands."""
    vehicles = []
    
    for brand in MACHINE_BRANDS:
        # Look for: "Brand" followed by model number/name
        pattern = rf'{brand}\s+([0-9A-Z\s]+?)(?:\s+(?:20\d{{2}})|Uregistrert|-|\n)'
        
        for match in re.finditer(pattern, text, re.I):
            model = match.group(1).strip()
            
            # Clean up model (remove trailing junk)
            model = re.sub(r'\s+(Uregistrert|-).*$', '', model).strip()
            
            # Find year nearby
            pos = match.start()
            window = text[max(0, pos-100):min(len(text), pos+400)]
            year_match = re.search(r'\b(20\d{2})\b', window)
            year = year_match.group(1) if year_match else "2024"
            
            vehicles.append({
                "registration": "Uregistrert",
                "vehicle_type": "traktor",
                "make_model_year": f"{brand} {model} {year}",
                "coverage": "kasko",
                "leasing": "",
                "annual_mileage": "",
                "deductible": "",
                "insurance_sum": "", "odometer": "", "bonus": "",
            })
    
    return vehicles


def _extract_all_registrations(text: str) -> list:
    """Find ALL registration numbers and their vehicles."""
    vehicles = []
    
    # Pattern: ANY text + year + registration
    # This is SUPER permissive
    pattern = r'([A-Z][A-Z0-9\s\-().]+?)\s+(\d{4})\s+([A-Z]{2}\s?\d{5})'
    
    for match in re.finditer(pattern, text, re.MULTILINE):
        make_model_raw = match.group(1).strip()
        year = match.group(2).strip()
        reg = match.group(3).strip().replace(" ", "")
        
        # Clean up make/model
        make_model = _clean_make_model(make_model_raw)
        
        # Skip if it doesn't contain a known car brand
        if not any(brand in make_model.upper() for brand in CAR_BRANDS):
            continue
        
        vehicles.append({
            "registration": reg,
            "vehicle_type": "bil",
            "make_model_year": f"{make_model} {year}",
            "coverage": "kasko",
            "leasing": _find_leasing(text, reg),
            "annual_mileage": "16 000",
            "deductible": "",
            "insurance_sum": "", "odometer": "", "bonus": "",
        })
    
    return vehicles


def _clean_make_model(text: str) -> str:
    """Clean up make/model."""
    # Remove company suffixes
    text = re.sub(r'^(AS|ASA|E)\s+', '', text)
    text = re.sub(r'\s+(AS|ASA)$', '', text)
    # Remove extra spaces
    text = ' '.join(text.split())
    return text.strip()


def _find_year(text: str, reg: str) -> str:
    """Find year for registration."""
    pattern = rf'{reg}.*?(?:Årsmodell|År|registrert):\s*(\d{{4}})'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else "2024"


def _find_leasing(text: str, reg: str) -> str:
    """Find leasing company."""
    if reg == "Uregistrert":
        return ""
    
    pos = text.find(reg)
    if pos == -1:
        return ""
    
    window = text[max(0, pos-200):min(len(text), pos+500)]
    
    companies = ["Sparebank 1", "Nordea Finans", "Santander", "DNB Finans", "BRAGE FINANS"]
    for company in companies:
        if company in window:
            return company
    
    return "Ja" if re.search(r'(leasing|tredjemannsinteresse)', window, re.I) else ""


def _categorize_all(vehicles: list) -> dict:
    """Categorize all vehicles."""
    categorized = {
        "car": [], "trailer": [], "moped": [], "tractor": [], "boat": [],
    }
    
    for v in vehicles:
        vtype = v.get("vehicle_type", "").lower()
        make = v.get("make_model_year", "").lower()
        
        if "tilhenger" in vtype:
            category = "trailer"
        elif "moped" in vtype:
            category = "moped"
        elif "traktor" in vtype or any(brand.lower() in make for brand in MACHINE_BRANDS):
            category = "tractor"
        elif "båt" in vtype:
            category = "boat"
        else:
            category = "car"
        
        categorized[category].append(v)
    
    return categorized


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
    
    total = 0
    
    for category, vehicles in categorized.items():
        if not vehicles:
            continue
        
        config = VEHICLE_ROWS[category]
        start, end, name = config["start"], config["end"], config["name"]
        
        st.write(f"  📌 {name}: Rows {start}-{end}")
        
        for idx, vehicle in enumerate(vehicles):
            row = start + idx
            
            if row > end:
                st.warning(f"  ⚠️ Too many {name}!")
                break
            
            for field, column in VEHICLE_COLUMNS.items():
                out[f"{column}{row}"] = vehicle.get(field, "")
            
            st.write(f"    Row {row}: {vehicle['registration']} - {vehicle['make_model_year']}")
            total += 1
    
    st.success(f"✅ Mapped {total} vehicles")
    
    return out


CELL_MAP = {}
