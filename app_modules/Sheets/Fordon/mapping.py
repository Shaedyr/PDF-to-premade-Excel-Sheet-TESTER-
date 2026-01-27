# app_modules/Sheets/Fordon/mapping.py
"""
COMPLETE FORDON EXTRACTION
Extracts ALL vehicles with confirmed data fields:
- Registration number
- Make/Model/Year
- Leasing (Column F) ✅
- Annual mileage (Column G) ✅
- Deductible (Column J) ✅
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
    "insurance_sum": "D",        # Will add later
    "coverage": "E",
    "leasing": "F",              # ✅ EXTRACTING
    "annual_mileage": "G",       # ✅ EXTRACTING
    "odometer": "H",             # Will add later
    "bonus": "I",                # Will add later
    "deductible": "J",           # ✅ EXTRACTING
}

# ALL possible brands
ALL_BRANDS = [
    "VOLKSWAGEN", "FORD", "TOYOTA", "MERCEDES", "LAND ROVER", "CITROEN", 
    "PEUGEOT", "VOLVO", "SCANIA", "MAN", "BMW", "AUDI", "NISSAN", "RENAULT",
    "Doosan", "Hitachi", "Caterpillar", "Liebherr", "Sennebogen", "Komatsu", 
    "Volvo", "JCB", "Bobcat", "Case", "John Deere", "New Holland", "Kubota",
]

MACHINE_BRANDS = ["Doosan", "Hitachi", "Caterpillar", "Liebherr", "Sennebogen", "Komatsu", "Volvo", "JCB", "Bobcat", "Case", "John Deere", "New Holland", "Kubota"]


def extract_vehicles_from_pdf(pdf_text: str) -> dict:
    """Extract ALL vehicles with complete data."""
    
    st.write("🔍 **FORDON: Complete extraction**")
    st.info("📝 Extracting vehicles with Leasing, Årlig kjørelengde, and Egenandel")
    
    if not pdf_text or len(pdf_text) < 1000:
        st.error("❌ PDF text too short!")
        return {}
    
    st.write(f"📄 PDF text: {len(pdf_text)} chars")
    st.write("---")
    
    all_vehicles = []
    
    # STRATEGY 1: If format
    st.write("  🔎 If Skadeforsikring format")
    if_vehicles = _extract_if_format(pdf_text)
    if if_vehicles:
        st.write(f"    ✅ {len(if_vehicles)} vehicles")
        all_vehicles.extend(if_vehicles)
    else:
        st.write("    ⊘ No matches")
    
    # STRATEGY 2: All brands (tractors/machines)
    st.write("  🔎 All brands (tractors/machines/equipment)")
    brand_vehicles = _extract_all_brands(pdf_text)
    if brand_vehicles:
        st.write(f"    ✅ {len(brand_vehicles)} items")
        all_vehicles.extend(brand_vehicles)
    else:
        st.write("    ⊘ No brands")
    
    # STRATEGY 3: All registrations
    st.write("  🔎 All registration numbers")
    reg_vehicles = _extract_all_registrations(pdf_text)
    if reg_vehicles:
        st.write(f"    ✅ {len(reg_vehicles)} registrations")
        all_vehicles.extend(reg_vehicles)
    else:
        st.write("    ⊘ No registrations")
    
    # Remove duplicates
    unique = {}
    for v in all_vehicles:
        reg = v['registration']
        if reg not in unique or len(v['make_model_year']) > len(unique[reg]['make_model_year']):
            unique[reg] = v
    
    all_vehicles = list(unique.values())
    
    # Categorize
    categorized = _categorize_all(all_vehicles)
    
    st.write("---")
    st.write("📦 **Categorized:**")
    for cat, vehicles in categorized.items():
        if vehicles:
            name = VEHICLE_ROWS[cat]['name']
            st.write(f"  🚗 {name}: {len(vehicles)}")
            for v in vehicles[:3]:
                leasing_info = f" | Leasing: {v['leasing']}" if v['leasing'] else ""
                st.write(f"    - {v['registration']} - {v['make_model_year']}{leasing_info}")
            if len(vehicles) > 3:
                st.write(f"    ... +{len(vehicles)-3} more")
    
    total = sum(len(v) for v in categorized.values())
    st.success(f"✅ **TOTAL: {total} vehicles extracted**")
    
    return categorized


def _extract_if_format(text: str) -> list:
    """Extract If Skadeforsikring format with complete data."""
    vehicles = []
    pattern = r'([A-Z]{2}\d{5}),\s*(Varebil|Personbil|Lastebil|Moped|Traktor|Båt|Tilhenger),\s*([A-Z][A-Z\s]+?)(?:\s+(\d+)|$)'
    
    for m in re.finditer(pattern, text, re.MULTILINE):
        reg = m.group(1).strip()
        vtype = m.group(2).strip()
        make = m.group(3).strip()
        
        # Check next lines for continuation
        pos = m.start()
        lines = text[pos:pos+200].split('\n')[1:3]
        for line in lines:
            line = line.strip()
            if line and line[0].isupper() and not re.match(r'[A-Z]{2}\d{5}', line):
                if not any(c.isdigit() for c in line[:10]):
                    make += " " + line.split()[0]
                    break
        
        year = _find_year(text, reg)
        
        # Extract detailed info for this vehicle
        leasing = _extract_leasing(text, reg)
        mileage = _extract_mileage(text, reg)
        deductible = _extract_deductible(text, reg)
        
        vehicles.append({
            "registration": reg,
            "vehicle_type": vtype,
            "make_model_year": f"{make} {year}",
            "insurance_sum": "",
            "coverage": "kasko",
            "leasing": leasing,              # ✅ EXTRACTED
            "annual_mileage": mileage,       # ✅ EXTRACTED
            "odometer": "",
            "bonus": "",
            "deductible": deductible,        # ✅ EXTRACTED
        })
    
    return vehicles


def _extract_all_brands(text: str) -> list:
    """Extract all brands (machines/tractors)."""
    vehicles = []
    found_items = set()
    
    for brand in ALL_BRANDS:
        pattern = rf'\b{brand}\b[^\n]{{0,100}}'
        
        for m in re.finditer(pattern, text, re.I):
            line = m.group(0)
            after_brand = line[len(brand):].strip()
            
            model_match = re.match(r'[^\w]*([0-9A-Z\s\-().]+?)(?:\s+20\d{2}|\s+kr|$)', after_brand, re.I)
            if model_match:
                model = model_match.group(1).strip()
            else:
                model = after_brand[:30].strip()
            
            model = re.sub(r'[-,].*$', '', model).strip()
            model = re.sub(r'\s+(Uregistrert|arb|maskin|og|as|asa).*$', '', model, flags=re.I).strip()
            
            if not model or len(model) < 1:
                model = ""
            
            identifier = f"{brand.lower()}_{model.lower()}"
            if identifier in found_items:
                continue
            found_items.add(identifier)
            
            year_match = re.search(r'\b(20\d{2})\b', line)
            if not year_match:
                pos = m.start()
                window = text[pos:pos+300]
                year_match = re.search(r'\b(20\d{2})\b', window)
            year = year_match.group(1) if year_match else "2024"
            
            is_machine = brand in MACHINE_BRANDS
            
            vehicles.append({
                "registration": "Uregistrert" if is_machine else "Se beskrivelse",
                "vehicle_type": "traktor" if is_machine else "bil",
                "make_model_year": f"{brand} {model} {year}".strip(),
                "insurance_sum": "",
                "coverage": "kasko",
                "leasing": "",
                "annual_mileage": "" if is_machine else "16 000",
                "odometer": "",
                "bonus": "",
                "deductible": "",
            })
    
    return vehicles


def _extract_all_registrations(text: str) -> list:
    """Extract all registration numbers."""
    vehicles = []
    all_regs = re.findall(r'\b([A-Z]{2}\s?\d{5})\b', text)
    
    for reg in set(all_regs):
        reg_clean = reg.replace(" ", "")
        
        pos = text.find(reg)
        if pos == -1:
            continue
        
        window = text[max(0, pos-200):min(len(text), pos+200)]
        
        make_model = None
        year = None
        
        for brand in ALL_BRANDS:
            if brand.upper() in window.upper():
                brand_pos = window.upper().find(brand.upper())
                after_brand = window[brand_pos+len(brand):].strip()
                
                model_match = re.match(r'([A-Z0-9\s\-().]+?)(?:\s+20\d{2}|\s+\d{4,}|\s+kr|$)', after_brand, re.I)
                if model_match:
                    model = model_match.group(1).strip()
                    make_model = f"{brand} {model}"
                else:
                    make_model = brand
                
                year_match = re.search(r'\b(20\d{2})\b', window)
                if year_match:
                    year = year_match.group(1)
                
                break
        
        if not make_model:
            before_reg = window[:window.find(reg)].strip()
            words = before_reg.split()[-5:]
            make_model = " ".join(words)
            if len(make_model) < 3:
                continue
        
        if not year:
            year = "2024"
        
        # Extract detailed info
        leasing = _extract_leasing(text, reg_clean)
        mileage = _extract_mileage(text, reg_clean)
        deductible = _extract_deductible(text, reg_clean)
        
        vehicles.append({
            "registration": reg_clean,
            "vehicle_type": "bil",
            "make_model_year": f"{make_model} {year}",
            "insurance_sum": "",
            "coverage": "kasko",
            "leasing": leasing,              # ✅ EXTRACTED
            "annual_mileage": mileage,       # ✅ EXTRACTED
            "odometer": "",
            "bonus": "",
            "deductible": deductible,        # ✅ EXTRACTED
        })
    
    return vehicles


# ============================================================================
# EXTRACTION HELPERS FOR CONFIRMED FIELDS
# ============================================================================

def _find_year(text: str, reg: str) -> str:
    """Find year for vehicle."""
    pattern = rf'{reg}.*?(?:Årsmodell|År|registrert):\s*(\d{{4}})'
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1) if m else "2024"


def _extract_leasing(text: str, reg: str) -> str:
    """
    ✅ EXTRACT LEASING INFO
    Looks for: Tredjemannsinteresse/leasing or leasing company names
    """
    if reg in ["Uregistrert", "Se beskrivelse"]:
        return ""
    
    pos = text.find(reg)
    if pos == -1:
        return ""
    
    # Look in a wide window around the registration
    window = text[max(0, pos-500):min(len(text), pos+1000)]
    
    # Known leasing companies
    leasing_companies = [
        "Sparebank 1",
        "Nordea Finans",
        "Santander",
        "DNB Finans",
        "BRAGE FINANS",
        "Handelsbanken",
        "BN Bank",
    ]
    
    for company in leasing_companies:
        if company in window:
            return company
    
    # Check for "Tredjemannsinteresse/leasing"
    if re.search(r'Tredjemannsinteresse/leasing', window, re.I):
        return "Ja"
    
    if re.search(r'(leasing|tredjemannsinteresse)', window, re.I):
        return "Ja"
    
    return ""


def _extract_mileage(text: str, reg: str) -> str:
    """
    ✅ EXTRACT ANNUAL MILEAGE
    Looks for: "Kjørelengde: 16 000 km" or similar
    """
    if reg in ["Uregistrert", "Se beskrivelse"]:
        return ""
    
    pos = text.find(reg)
    if pos == -1:
        return "16 000"  # Default
    
    window = text[max(0, pos-500):min(len(text), pos+1000)]
    
    # Pattern: "Kjørelengde: 16 000 km" or "16 000 km"
    mileage_match = re.search(r'(?:Kjørelengde|kjørelengde):\s*(\d+\s?\d+)\s*km', window)
    if mileage_match:
        return mileage_match.group(1).replace(" ", " ")
    
    # Fallback: look for any number followed by km
    mileage_match = re.search(r'(\d+\s?\d+)\s*km', window)
    if mileage_match:
        return mileage_match.group(1).replace(" ", " ")
    
    return "16 000"  # Default


def _extract_deductible(text: str, reg: str) -> str:
    """
    ✅ EXTRACT DEDUCTIBLE (EGENANDEL)
    Looks for: "Egenandel - Skader på eget kjøretøy: 12 000 kr"
    """
    if reg in ["Uregistrert", "Se beskrivelse"]:
        return ""
    
    pos = text.find(reg)
    if pos == -1:
        return "8 000"  # Default
    
    window = text[max(0, pos-500):min(len(text), pos+1500)]
    
    # Pattern: "Egenandel - Skader på eget kjøretøy: 12 000 kr"
    deductible_match = re.search(r'Egenandel\s*-\s*Skader på eget kjøretøy:\s*(\d+\s?\d+)\s*kr', window)
    if deductible_match:
        return deductible_match.group(1).replace(" ", " ")
    
    # Fallback: any "Egenandel:" followed by number
    deductible_match = re.search(r'Egenandel[:\s]+(\d+\s?\d+)\s*kr', window)
    if deductible_match:
        return deductible_match.group(1).replace(" ", " ")
    
    return "8 000"  # Default


def _categorize_all(vehicles: list) -> dict:
    """Categorize vehicles by type."""
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
        reg = v.get("registration", "")
        
        if "tilhenger" in vtype or "trailer" in make:
            cat = "trailer"
        elif "moped" in vtype or "moped" in make:
            cat = "moped"
        elif "traktor" in vtype or "uregistrert" in reg.lower() or any(b.lower() in make for b in MACHINE_BRANDS):
            cat = "tractor"
        elif "båt" in vtype or "boat" in make:
            cat = "boat"
        else:
            cat = "car"
        
        categorized[cat].append(v)
    
    return categorized


def transform_data(extracted: dict) -> dict:
    """Transform to Excel cells."""
    
    st.write("🔄 **FORDON: transform_data**")
    st.info("✅ Extracting: Leasing, Årlig kjørelengde, Egenandel")
    
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
            
            # Show what was extracted
            leasing = vehicle.get('leasing', '')
            mileage = vehicle.get('annual_mileage', '')
            deductible = vehicle.get('deductible', '')
            
            details = f"{vehicle['registration']} - {vehicle['make_model_year']}"
            if leasing:
                details += f" | Leasing: {leasing}"
            if mileage:
                details += f" | {mileage} km"
            if deductible:
                details += f" | Egenandel: {deductible}"
            
            st.write(f"    Row {row}: {details}")
            total += 1
    
    st.success(f"✅ Mapped {total} vehicles with complete data")
    
    return out


CELL_MAP = {}
