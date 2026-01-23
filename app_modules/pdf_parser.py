import streamlit as st
import pdfplumber
import re
from io import BytesIO

# ---------------------------------------------------------
# REGEX PATTERNS (FIXED!)
# ---------------------------------------------------------

ORG_RE = re.compile(r"\b(\d{9})\b")
ORG_IN_TEXT_RE = re.compile(
    r"(organisasjonsnummer|org\.?nr|org nr|orgnummer)[:\s]*?(\d{9})",
    flags=re.I
)

# FIXED: Less greedy pattern, stops at line breaks
COMPANY_WITH_SUFFIX_RE = re.compile(
    r"([A-ZÆØÅ][A-Za-zÆØÅæøå0-9.\-&]{1,60}?)\s+(AS|ASA|ANS|DA|ENK|KS|BA)\b",
    flags=re.I
)

POST_CITY_RE = re.compile(
    r"(\d{4})\s+([A-ZÆØÅa-zæøå\-\s]{2,50})"
)

ADDRESS_RE = re.compile(
    r"([A-ZÆØÅa-zæøå.\-\s]{3,60}\s+\d{1,4}[A-Za-z]?)"
)

REVENUE_RE = re.compile(
    r"omsetning\s*(?:2024)?[:\s]*([\d\s\.,]+(?:kr)?)",
    flags=re.I
)

DEADLINE_RE = re.compile(
    r"(?:anbudsfrist|frist)[:\s]*([0-3]?\d[./-][01]?\d[./-]\d{2,4})",
    flags=re.I
)

# Companies to COMPLETELY IGNORE (exact match)
IGNORE_COMPANIES_EXACT = [
    "AS FORSIKRINGSMEGLING",
    "IF SKADEFORSIKRING NUF",
    "IF SKADEFORSIKRING AB",
    "GJENSIDIGE FORSIKRING ASA",
    "TRYG FORSIKRING",
]

# Keywords in company name to ignore (partial match)
IGNORE_KEYWORDS = [
    "FORSIKRINGSMEGLING",
    "INSURANCE",
    "MEGLING",
]

# Vehicle section keywords
VEHICLE_KEYWORDS = [
    "kjøretøyforsikring",
    "næringsbil",
    "varebil",
    "personbil",
    "registreringsnummer",
    "årsmodell",
]

# ---------------------------------------------------------
# SMART PDF TEXT EXTRACTION
# ---------------------------------------------------------

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    SMART extraction: Finds vehicle section automatically.
    """

    # Handle Streamlit UploadedFile objects
    if hasattr(pdf_bytes, 'read'):
        pdf_bytes = pdf_bytes.read()

    if not pdf_bytes:
        st.warning("⚠️ No PDF bytes provided")
        return ""

    st.write(f"📄 **Smart PDF extraction** ({len(pdf_bytes)} bytes)")

    try:
        text = ""
        vehicle_section_found = False
        pages_after_vehicles = 0
        max_pages_to_read = 50
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            st.success(f"✅ PDF: {total_pages} pages")
            st.info("🔍 Searching for vehicle section...")
            
            for i, page in enumerate(pdf.pages):
                if i >= max_pages_to_read:
                    st.warning(f"⚠️ Reached {max_pages_to_read} pages, stopping")
                    break
                
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
                    
                    # Check for vehicle keywords
                    page_lower = extracted.lower()
                    has_vehicle_keywords = any(kw in page_lower for kw in VEHICLE_KEYWORDS)
                    
                    if has_vehicle_keywords:
                        if not vehicle_section_found:
                            st.success(f"🚗 Vehicle section found at page {i+1}!")
                            vehicle_section_found = True
                        pages_after_vehicles = 0
                        st.write(f"  ✓ Page {i+1}: {len(extracted)} chars (vehicles)")
                    else:
                        if vehicle_section_found:
                            pages_after_vehicles += 1
                            st.write(f"  · Page {i+1}: {len(extracted)} chars")
                            
                            # Stop if 5 pages without vehicle keywords
                            if pages_after_vehicles >= 5:
                                st.success(f"✅ Vehicle section ended at page {i+1}")
                                break
                        else:
                            # Before vehicle section
                            if i < 10 or i % 5 == 0:
                                st.write(f"  · Page {i+1}: {len(extracted)} chars")
        
        if text:
            st.success(f"✅ **Total: {len(text)} chars from {i+1} pages**")
        else:
            st.error("❌ No text extracted!")
        
        return text

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return ""

# ---------------------------------------------------------
# FIELD EXTRACTION (FIXED COMPANY DETECTION!)
# ---------------------------------------------------------

def extract_fields_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extracts fields from PDF with IMPROVED company name detection.
    """
    
    st.write("=" * 50)
    st.write("🔍 **PDF PARSER**")
    st.write("=" * 50)

    txt = extract_text_from_pdf(pdf_bytes)
    fields = {}

    if not txt:
        st.error("❌ No text extracted")
        return fields

    # IMPORTANT: Store full text
    fields["pdf_text"] = txt
    st.write(f"✓ Added 'pdf_text' ({len(txt)} chars)")

    # 1) Org number
    m = ORG_IN_TEXT_RE.search(txt)
    if m:
        fields["org_number"] = m.group(2)
        st.write(f"✓ Org number: {m.group(2)}")
    else:
        m2 = ORG_RE.search(txt)
        if m2:
            fields["org_number"] = m2.group(1)
            st.write(f"✓ Org number: {m2.group(1)}")

    # 2) Company name - IMPROVED FILTERING!
    st.write("🔍 Searching for company name...")
    
    # Split text into lines to avoid matching across line breaks
    lines = txt.split('\n')
    candidates = []
    
    for line in lines:
        matches = COMPANY_WITH_SUFFIX_RE.finditer(line)
        for m3 in matches:
            company = m3.group(0).strip()
            
            # Skip if too short
            if len(company) < 5:
                continue
            
            # Check exact ignore list
            if company.upper() in [c.upper() for c in IGNORE_COMPANIES_EXACT]:
                st.write(f"  ⊘ Ignored (exact): {company}")
                continue
            
            # Check keyword ignore list
            if any(kw.upper() in company.upper() for kw in IGNORE_KEYWORDS):
                st.write(f"  ⊘ Ignored (keyword): {company}")
                continue
            
            # This looks like a real company!
            candidates.append(company)
            st.write(f"  ✓ Candidate: {company}")
    
    # Pick the first valid candidate
    if candidates:
        fields["company_name"] = candidates[0]
        st.success(f"✅ Selected company: {candidates[0]}")
    else:
        st.warning("⚠️ No company name found")

    # 3) Postal code + city
    mpc = POST_CITY_RE.search(txt)
    if mpc:
        fields["post_nr"] = mpc.group(1)
        fields["city"] = mpc.group(2).strip()
        st.write(f"✓ Postal: {mpc.group(1)} {mpc.group(2).strip()}")

    # 4) Address
    maddr = ADDRESS_RE.search(txt)
    if maddr:
        fields["address"] = maddr.group(1).strip()
        st.write(f"✓ Address: {maddr.group(1).strip()}")

    # 5) Revenue
    mrev = REVENUE_RE.search(txt)
    if mrev:
        fields["revenue_2024"] = mrev.group(1).strip()
        st.write(f"✓ Revenue: {mrev.group(1).strip()}")

    # 6) Deadline
    mdate = DEADLINE_RE.search(txt)
    if mdate:
        fields["tender_deadline"] = mdate.group(1).strip()
        st.write(f"✓ Deadline: {mdate.group(1).strip()}")

    st.write("=" * 50)
    st.success(f"✅ Returning {len(fields)} fields")
    st.write("=" * 50)

    return fields

# ---------------------------------------------------------
# PAGE VIEW
# ---------------------------------------------------------
def run():
    st.title("📄 PDF Parser Module")
    st.write("Smart extraction with improved company detection")
