# app_modules/Sheets/Fordon/mapping.py
"""
MAXIMUM EXTRACTION MODE
Extracts EVERYTHING that could possibly be a vehicle/equipment
Better to have too many than miss something - human will remove extras
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

# ALL possible brands - cars, trucks, tractors, equipment
ALL_BRANDS = [
    # Cars/Trucks
    "VOLKSWAGEN", "FORD", "TOYOTA", "MERCEDES", "LAND ROVER", "CITROEN", 
    "PEUGEOT", "VOLVO", "SCANIA", "MAN", "BMW", "AUDI", "NISSAN", "RENAULT",
    # Tractors/Machines
    "Doosan", "Hitachi", "Caterpillar", "Liebherr", "Sennebogen", "Komatsu", 
    "Volvo", "JCB", "Bobcat", "Case", "John Deere", "New Holland", "Kubota",
]

MACHINE_BRANDS = ["Doosan", "Hitachi", "Caterpillar", "Liebherr", "Sennebogen", "Komatsu", "Volvo", "JCB", "Bobcat", "Case", "John Deere", "New Holland", "Kubota"]


def extract_vehicles_from_pdf(pdf_text: str) -> dict:
    """MAXIMUM extraction - get everything!"""
    
    st.write("🔍 **FORDON: MAXIMUM EXTRACTION MODE**")
    st.info("📝 Extracting ALL vehicles/equipment - you can remove extras manually")
    
    if not pdf_text or len(pdf_text) < 1000:
        st.error("❌ PDF text too short!")
        return {}
    
    st.write(f"📄 PDF text: {len(pdf_text)} chars")
    st.write("---")
    
    all_vehicles = []
    
    # STRATEGY 1: If format (if it exists)
    st.write("  🔎 If Skadeforsikring format")
    if_vehicles = _extract_if_format(pdf_text)
    if if_vehicles:
        st.write(f"    ✅ {len(if_vehicles)} vehicles")
        all_vehicles.extend(if_vehicles)
    else:
        st.write("    ⊘ No matches")
    
    # STRATEGY 2: ALL brands (machines, tractors, equipment)
    st.write("  🔎 All brands (tractors/machines/equipment)")
    brand_vehicles = _extract_all_brands(pdf_text)
    if brand_vehicles:
        st.write(f"    ✅ {len(brand_vehicles)} items")
        all_vehicles.extend(brand_vehicles)
    else:
        st.write("    ⊘ No brands")
    
    # STRATEGY 3: ALL registration numbers with ANY text around them
    st.write("  🔎 All registration numbers")
    reg_vehicles = _extract_all_registrations(pdf_text)
    if reg_vehicles:
        st.write(f"    ✅ {len(reg_vehicles)} registrations")
        all_vehicles.extend(reg_vehicles)
    else:
        st.write("    ⊘ No registrations")
    
    # Remove duplicates by registration
    unique = {}
    for v in all_vehicles:
        reg = v['registration']
        # Keep the one with most info (longest make_model_year)
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
                st.write(f"    - {v['registration']} - {v['make_model_year']}")
            if len(vehicles) > 3:
                st.write(f"    ... +{len(vehicles)-3} more")
    
    total = sum(len(v) for v in categorized.values())
    st.success(f"✅ **TOTAL: {total} vehicles/items extracted**")
    st.info("💡 Review in Excel and remove any that aren't needed")
    
    return categorized


def _extract_if_format(text: str) -> list:
    """Extract If Skadeforsikring format."""
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


def _extract_all_brands(text: str) -> list:
    """Extract EVERY brand mention with a model."""
    vehicles = []
    found_items = set()  # Track what we've found to avoid duplicates
    
    for brand in ALL_BRANDS:
        # VERY permissive pattern: Brand + anything up to 100 chars
        pattern = rf'\b{brand}\b[^\n]{{0,100}}'
        
        for m in re.finditer(pattern, text, re.I):
            line = m.group(0)
            
            # Extract what comes after the brand
            after_brand = line[len(brand):].strip()
            
            # Try to extract model (numbers and letters)
            model_match = re.match(r'[^\w]*([0-9A-Z\s\-().]+?)(?:\s+20\d{2}|\s+kr|$)', after_brand, re.I)
            if model_match:
                model = model_match.group(1).strip()
            else:
                model = after_brand[:30].strip()
            
            # Clean model
            model = re.sub(r'[-,].*$', '', model).strip()
            model = re.sub(r'\s+(Uregistrert|arb|maskin|og|as|asa).*$', '', model, flags=re.I).strip()
            
            if not model or len(model) < 1:
                model = ""
            
            # Create identifier to avoid duplicates
            identifier = f"{brand.lower()}_{model.lower()}"
            if identifier in found_items:
                continue
            found_items.add(identifier)
            
            # Find year
            year_match = re.search(r'\b(20\d{2})\b', line)
            if not year_match:
                pos = m.start()
                window = text[pos:pos+300]
                year_match = re.search(r'\b(20\d{2})\b', window)
            year = year_match.group(1) if year_match else "2024"
            
            # Determine if it's a tractor/machine or car
            is_machine = brand in MACHINE_BRANDS
            
            vehicles.append({
                "registration": "Uregistrert" if is_machine else "Se beskrivelse",
                "vehicle_type": "traktor" if is_machine else "bil",
                "make_model_year": f"{brand} {model} {year}".strip(),
                "coverage": "kasko",
                "leasing": "",
                "annual_mileage": "" if is_machine else "16 000",
                "deductible": "",
                "insurance_sum": "", "odometer": "", "bonus": "",
            })
    
    return vehicles


def _extract_all_registrations(text: str) -> list:
    """Extract EVERY registration number with surrounding text."""
    vehicles = []
    
    # Find ALL registration numbers
    all_regs = re.findall(r'\b([A-Z]{2}\s?\d{5})\b', text)
    
    st.write(f"      Found {len(set(all_regs))} unique registration numbers")
    
    for reg in set(all_regs):
        reg_clean = reg.replace(" ", "")
        
        # Find text around registration
        pos = text.find(reg)
        if pos == -1:
            continue
        
        # Wide window to catch all context
        window = text[max(0, pos-200):min(len(text), pos+200)]
        
        # Try to find ANY brand
        make_model = None
        year = None
        
        for brand in ALL_BRANDS:
            if brand.upper() in window.upper():
                # Found brand
                brand_pos = window.upper().find(brand.upper())
                after_brand = window[brand_pos+len(brand):].strip()
                
                # Extract model
                model_match = re.match(r'([A-Z0-9\s\-().]+?)(?:\s+20\d{2}|\s+\d{4,}|\s+kr|$)', after_brand, re.I)
                if model_match:
                    model = model_match.group(1).strip()
                    make_model = f"{brand} {model}"
                else:
                    make_model = brand
                
                # Find year
                year_match = re.search(r'\b(20\d{2})\b', window)
                if year_match:
                    year = year_match.group(1)
                
                break
        
        if not make_model:
            # No brand found - extract whatever is near the registration
            # Pattern: text before registration might be make/model
            before_reg = window[:window.find(reg)].strip()
            words = before_reg.split()[-5:]  # Last 5 words before registration
            make_model = " ".join(words)
            
            # If still nothing useful, skip
            if len(make_model) < 3:
                continue
        
        if not year:
            year = "2024"
        
        vehicles.append({
            "registration": reg_clean,
            "vehicle_type": "bil",
            "make_model_year": f"{make_model} {year}",
            "coverage": "kasko",
            "leasing": _find_leasing(text, reg_clean),
            "annual_mileage": "16 000",
            "deductible": "",
            "insurance_sum": "", "odometer": "", "bonus": "",
        })
    
    return vehicles


def _find_year(text: str, reg: str) -> str:
    """Find year for registration."""
    pattern = rf'{reg}.*?(?:Årsmodell|År|registrert):\s*(\d{{4}})'
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1) if m else "2024"


def _find_leasing(text: str, reg: str) -> str:
    """Find leasing info."""
    if reg in ["Uregistrert", "Se beskrivelse"]:
        return ""
    
    pos = text.find(reg)
    if pos == -1:
        return ""
    
    window = text[max(0, pos-200):min(len(text), pos+500)]
    
    companies = ["Sparebank 1", "Nordea Finans", "Santander", "DNB Finans", "BRAGE FINANS"]
    for c in companies:
        if c in window:
            return c
    
    return "Ja" if re.search(r'(leasing|tredjemannsinteresse)', window, re.I) else ""


def _categorize_all(vehicles: list) -> dict:
    """Categorize all vehicles."""
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
        
        # Categorize
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
                st.warning(f"  ⚠️ Too many {name}! Increase row range in Excel template.")
                break
            
            for field, column in VEHICLE_COLUMNS.items():
                out[f"{column}{row}"] = vehicle.get(field, "")
            
            st.write(f"    Row {row}: {vehicle['registration']} - {vehicle['make_model_year']}")
            total += 1
    
    st.success(f"✅ Mapped {total} vehicles/items")
    st.info("💡 Review and remove any unwanted entries manually")
    
    return out


CELL_MAP = {}
