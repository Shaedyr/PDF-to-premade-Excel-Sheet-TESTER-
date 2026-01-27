# app_modules/Sheets/Fordon/mapping.py
"""
FIXED FORDON EXTRACTION - V2
Fixes:
- Accurate vehicle counting (no duplicates)
- Better model extraction (includes machine type)
- Bonus extraction
- Better leasing detection
- Boat motor type extraction
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
    # D removed - not needed
    "coverage": "E",
    "leasing": "F",
    "annual_mileage": "G",
    # H removed - not needed
    "bonus": "I",
    "deductible": "J",
}

CAR_BRANDS = ["VOLKSWAGEN", "FORD", "TOYOTA", "MERCEDES-BENZ", "MERCEDES", "LAND ROVER", "CITROEN", "PEUGEOT", "VOLVO", "SCANIA", "MAN", "BMW", "AUDI", "NISSAN", "RENAULT"]
MACHINE_BRANDS = ["Doosan", "Hitachi", "Caterpillar", "Liebherr", "Sennebogen", "Komatsu", "Volvo", "JCB", "Bobcat", "Case", "John Deere", "New Holland", "Kubota"]
MOPED_BRANDS = ["YAMAHA", "VESPA", "HONDA", "SUZUKI", "PIAGGIO", "APRILIA"]
BOAT_BRANDS = ["YAMARIN", "BUSTER", "QUICKSILVER", "FINNMASTER", "BELLA", "PIONER"]


def extract_vehicles_from_pdf(pdf_text: str) -> dict:
    """Extract vehicles with NO DUPLICATES."""
    
    st.write("🔍 **FORDON: Fixed extraction v2**")
    
    if not pdf_text or len(pdf_text) < 1000:
        st.error("❌ PDF text too short!")
        return {}
    
    st.write(f"📄 PDF text: {len(pdf_text)} chars")
    st.write("---")
    
    # Extract using If pattern ONLY (most reliable)
    st.write("  🔎 If Skadeforsikring format")
    vehicles = _extract_if_format_complete(pdf_text)
    
    if vehicles:
        st.write(f"    ✅ {len(vehicles)} vehicles")
    else:
        st.write("    ⊘ No matches")
        return {}
    
    # Categorize
    categorized = _categorize_all(vehicles)
    
    st.write("---")
    st.write("📦 **Categorized:**")
    for cat, vehs in categorized.items():
        if vehs:
            name = VEHICLE_ROWS[cat]['name']
            st.write(f"  🚗 {name}: {len(vehs)}")
            for v in vehs[:3]:
                bonus_txt = f" | Bonus: {v['bonus']}" if v['bonus'] else ""
                leasing_txt = f" | Leasing: {v['leasing']}" if v['leasing'] else ""
                st.write(f"    - {v['registration']} - {v['make_model_year']}{leasing_txt}{bonus_txt}")
            if len(vehs) > 3:
                st.write(f"    ... +{len(vehs)-3} more")
    
    total = sum(len(v) for v in categorized.values())
    st.success(f"✅ **TOTAL: {total} vehicles**")
    
    return categorized


def _extract_if_format_complete(text: str) -> list:
    """
    Extract If format with COMPLETE data.
    Pattern: REG, Type, MAKE
             MODEL (on next line sometimes)
    """
    vehicles = []
    seen_registrations = set()  # Track to avoid duplicates
    
    pattern = r'([A-Z]{2}\d{5}),\s*(Varebil|Personbil|Lastebil|Moped|Traktor|Båt|Tilhenger),\s*([A-Z][A-Z\s\-]+?)(?:\s+(\d+)|$)'
    
    for m in re.finditer(pattern, text, re.MULTILINE):
        reg = m.group(1).strip()
        
        # Skip if already found (avoid duplicates!)
        if reg in seen_registrations:
            continue
        seen_registrations.add(reg)
        
        vtype = m.group(2).strip()
        make = m.group(3).strip()
        
        # Get detailed section for this vehicle
        pos = m.start()
        # Get larger window (up to 1500 chars) to catch all details
        window = text[pos:min(len(text), pos+1500)]
        
        # Extract model from next few lines
        lines = window.split('\n')
        model_parts = [make]
        
        for i, line in enumerate(lines[1:6]):  # Check next 5 lines
            line = line.strip()
            if not line:
                continue
            
            # Stop if we hit another registration or section header
            if re.match(r'[A-Z]{2}\d{5}', line):
                break
            if line.startswith('===') or 'Årsmodell' in line:
                break
            
            # Check if line looks like a model name
            if line and line[0].isupper():
                # Not just a field name
                if ':' not in line[:20] and 'Kommune' not in line:
                    # This is likely model continuation
                    model_parts.append(line.split()[0] if line.split() else "")
                    # Stop after getting model
                    break
        
        make_model = " ".join(model_parts).strip()
        
        # Extract year
        year = _find_year_in_window(window, reg)
        
        # Extract all detailed fields
        leasing = _extract_leasing_in_window(window)
        mileage = _extract_mileage_in_window(window)
        deductible = _extract_deductible_in_window(window)
        bonus = _extract_bonus(text, reg)  # Global search for bonus
        motor_type = _extract_motor_type_in_window(window) if 'Båt' in vtype else ""
        
        # For boats, add motor type to model
        if motor_type and 'Båt' in vtype:
            make_model += f" ({motor_type})"
        
        vehicle = {
            "registration": reg,
            "vehicle_type": vtype,
            "make_model_year": f"{make_model} {year}",
            "coverage": "kasko",
            "leasing": leasing,
            "annual_mileage": mileage,
            "bonus": bonus,
            "deductible": deductible,
        }
        
        vehicles.append(vehicle)
    
    return vehicles


def _find_year_in_window(window: str, reg: str) -> str:
    """Find year in window."""
    year_match = re.search(r'Årsmodell:\s*(\d{4})', window)
    if year_match:
        return year_match.group(1)
    
    # Fallback: any 4-digit year
    year_match = re.search(r'\b(20[12]\d)\b', window)
    if year_match:
        return year_match.group(1)
    
    return "2024"


def _extract_leasing_in_window(window: str) -> str:
    """Extract leasing from window."""
    # Look for exact leasing line
    leasing_match = re.search(r'Tredjemannsinteresse/leasing:\s*([A-ZÆØÅa-zæøå0-9\s]+?)(?:\n|$)', window, re.I)
    if leasing_match:
        company = leasing_match.group(1).strip()
        return company if company else "Ja"
    
    # Check known companies
    companies = ["Sparebank 1", "Nordea Finans", "Santander", "DNB Finans", "BRAGE FINANS", "Handelsbanken", "BN Bank"]
    for company in companies:
        if company in window:
            return company
    
    # Generic check
    if re.search(r'(leasing|tredjemannsinteresse)', window, re.I):
        return "Ja"
    
    return ""


def _extract_mileage_in_window(window: str) -> str:
    """Extract mileage from window."""
    mileage_match = re.search(r'Kjørelengde:\s*(\d+\s?\d+)\s*km', window, re.I)
    if mileage_match:
        return mileage_match.group(1).replace(" ", " ")
    
    # Fallback
    mileage_match = re.search(r'(\d+\s?\d+)\s*km', window)
    if mileage_match:
        return mileage_match.group(1).replace(" ", " ")
    
    return ""


def _extract_deductible_in_window(window: str) -> str:
    """Extract deductible from window."""
    # Most specific pattern first
    deduct_match = re.search(r'Egenandel\s*-\s*Skader på eget kjøretøy:\s*(\d+\s?\d+)\s*kr', window)
    if deduct_match:
        return deduct_match.group(1).replace(" ", " ")
    
    # Generic egenandel
    deduct_match = re.search(r'Egenandel[:\s-]+(\d+\s?\d+)\s*kr', window)
    if deduct_match:
        return deduct_match.group(1).replace(" ", " ")
    
    return ""


def _extract_bonus(text: str, reg: str) -> str:
    """
    Extract bonus information.
    Usually in separate section: "AB12345: 60% bonus"
    """
    # Search globally for this registration's bonus
    bonus_match = re.search(rf'{reg}:\s*(\d+)%\s*bonus', text, re.I)
    if bonus_match:
        return bonus_match.group(1) + "%"
    
    # Alternative format
    bonus_match = re.search(rf'{reg}.*?bonus[:\s]*(\d+)%', text, re.I | re.DOTALL)
    if bonus_match:
        return bonus_match.group(1) + "%"
    
    return ""


def _extract_motor_type_in_window(window: str) -> str:
    """Extract boat motor type."""
    if re.search(r'innenbords\s*motor', window, re.I):
        return "innenbords motor"
    if re.search(r'utenbords\s*motor', window, re.I):
        return "utenbords motor"
    if re.search(r'påhengsmotor', window, re.I):
        return "påhengsmotor"
    return ""


def _categorize_all(vehicles: list) -> dict:
    """Categorize by type."""
    categorized = {
        "car": [],
        "trailer": [],
        "moped": [],
        "tractor": [],
        "boat": [],
    }
    
    for v in vehicles:
        vtype = v.get("vehicle_type", "").lower()
        make = v.get("make_model_year", "").lower()
        
        if "tilhenger" in vtype:
            cat = "trailer"
        elif "moped" in vtype:
            cat = "moped"
        elif "traktor" in vtype or "lastebil" in vtype:
            cat = "tractor"
        elif "båt" in vtype or "boat" in vtype:
            cat = "boat"
        else:
            cat = "car"
        
        categorized[cat].append(v)
    
    return categorized


def transform_data(extracted: dict) -> dict:
    """Transform to Excel."""
    
    st.write("🔄 **FORDON: transform_data**")
    st.info("✅ Extracting: Leasing, Årlig kjørelengde, Bonus, Egenandel")
    
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
    
    for cat, vehicles in categorized.items():
        if not vehicles:
            continue
        
        config = VEHICLE_ROWS[cat]
        start, end, name = config["start"], config["end"], config["name"]
        
        st.write(f"  📌 {name}: Rows {start}-{end}")
        
        for idx, vehicle in enumerate(vehicles):
            row = start + idx
            
            if row > end:
                st.warning(f"  ⚠️ Too many {name}!")
                break
            
            for field, column in VEHICLE_COLUMNS.items():
                out[f"{column}{row}"] = vehicle.get(field, "")
            
            # Show details
            details = f"{vehicle['registration']} - {vehicle['make_model_year']}"
            if vehicle.get('leasing'):
                details += f" | Leasing: {vehicle['leasing']}"
            if vehicle.get('annual_mileage'):
                details += f" | {vehicle['annual_mileage']} km"
            if vehicle.get('bonus'):
                details += f" | Bonus: {vehicle['bonus']}"
            if vehicle.get('deductible'):
                details += f" | Egenandel: {vehicle['deductible']}"
            
            st.write(f"    Row {row}: {details}")
            total += 1
    
    st.success(f"✅ Mapped {total} vehicles")
    
    return out


CELL_MAP = {}
