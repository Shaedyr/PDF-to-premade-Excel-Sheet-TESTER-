import streamlit as st
import pdfplumber
import re
from io import BytesIO

# ---------------------------------------------------------
# REGEX PATTERNS
# ---------------------------------------------------------

ORG_RE = re.compile(r"\b(\d{9})\b")
ORG_IN_TEXT_RE = re.compile(
    r"(organisasjonsnummer|org\.?nr|org nr|orgnummer)[:\s]*?(\d{9})",
    flags=re.I
)

COMPANY_WITH_SUFFIX_RE = re.compile(
    r"([A-ZÆØÅ][A-Za-zÆØÅæøå0-9.\-&\s]{1,120}?)\s+(AS|ASA|ANS|DA|ENK|KS|BA)\b",
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

# ---------------------------------------------------------
# PDF TEXT EXTRACTION (WITH DEBUG)
# ---------------------------------------------------------

def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF"""
    
    # Handle Streamlit UploadedFile objects
    if hasattr(pdf_bytes, 'read'):
        pdf_bytes = pdf_bytes.read()
    
    if not pdf_bytes:
        st.warning("⚠️ No PDF bytes provided")
        return ""
    
    st.write(f"📄 **Attempting to extract text from PDF** ({len(pdf_bytes)} bytes)")
    # ... rest of code

    try:
        text = ""
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            st.success(f"✅ PDF opened successfully! Found {len(pdf.pages)} pages")
            
            for i, page in enumerate(pdf.pages[:6]):
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
                    st.write(f"  ✓ Page {i+1}: {len(extracted)} characters extracted")
                else:
                    st.warning(f"  ⚠️ Page {i+1}: No text found (might be image-based)")
        
        if text:
            st.success(f"✅ **Total text extracted: {len(text)} characters**")
        else:
            st.error("❌ No text extracted from any page!")
            st.warning("This PDF might be:")
            st.write("• Image-based (scanned document) - needs OCR")
            st.write("• Encrypted or password-protected")
            st.write("• Corrupted")
        
        return text

    except Exception as e:
        st.error(f"❌ PDF extraction error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return ""

# ---------------------------------------------------------
# FIELD EXTRACTION
# ---------------------------------------------------------

def extract_fields_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extracts useful fields from a PDF:
    - org number
    - company name
    - address
    - post nr + city
    - revenue
    - deadline
    - pdf_text (full text for other sheets to use)
    """
    
    st.write("=" * 50)
    st.write("🔍 **PDF PARSER: extract_fields_from_pdf called**")
    st.write("=" * 50)

    txt = extract_text_from_pdf(pdf_bytes)
    fields = {}

    if not txt:
        st.error("❌ **No text extracted - returning empty fields**")
        return fields

    st.success(f"✅ **Text extracted! Adding to fields dictionary**")

    # IMPORTANT: Include full PDF text so other sheets (like Fordon) can parse it
    fields["pdf_text"] = txt
    st.write(f"✓ Added 'pdf_text' to fields ({len(txt)} chars)")

    # 1) Org number
    m = ORG_IN_TEXT_RE.search(txt)
    if m:
        fields["org_number"] = m.group(2)
        st.write(f"✓ Found org_number: {m.group(2)}")
    else:
        m2 = ORG_RE.search(txt)
        if m2:
            fields["org_number"] = m2.group(1)
            st.write(f"✓ Found org_number: {m2.group(1)}")

    # 2) Company name
    m3 = COMPANY_WITH_SUFFIX_RE.search(txt)
    if m3:
        fields["company_name"] = m3.group(0).strip()
        st.write(f"✓ Found company_name: {m3.group(0).strip()}")
    else:
        # fallback: first title-cased line
        for line in txt.splitlines():
            line = line.strip()
            if len(line) > 3 and line == line.title():
                fields["company_name"] = line
                st.write(f"✓ Found company_name (fallback): {line}")
                break

    # 3) Postnummer + city
    mpc = POST_CITY_RE.search(txt)
    if mpc:
        fields["post_nr"] = mpc.group(1)
        fields["city"] = mpc.group(2).strip()
        st.write(f"✓ Found postal: {mpc.group(1)} {mpc.group(2).strip()}")

    # 4) Address
    maddr = ADDRESS_RE.search(txt)
    if maddr:
        fields["address"] = maddr.group(1).strip()
        st.write(f"✓ Found address: {maddr.group(1).strip()}")

    # 5) Revenue
    mrev = REVENUE_RE.search(txt)
    if mrev:
        fields["revenue_2024"] = mrev.group(1).strip()
        st.write(f"✓ Found revenue: {mrev.group(1).strip()}")

    # 6) Deadline
    mdate = DEADLINE_RE.search(txt)
    if mdate:
        fields["tender_deadline"] = mdate.group(1).strip()
        st.write(f"✓ Found deadline: {mdate.group(1).strip()}")

    st.write("=" * 50)
    st.success(f"✅ **PDF PARSER: Returning {len(fields)} fields**")
    st.write(f"Fields: {list(fields.keys())}")
    st.write("=" * 50)

    return fields

# ---------------------------------------------------------
# PAGE VIEW (so it works as a selectable page)
# ---------------------------------------------------------
def run():
    st.title("📄 PDF Parser Module")
    st.write("Dette modulen ekstraherer tekst og felter fra PDF-dokumenter.")
    st.info("Brukes av hovedsiden for å hente data fra PDF.")

