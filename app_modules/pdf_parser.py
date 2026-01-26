import streamlit as st
import pdfplumber
import re
from io import BytesIO

# Try to import OCR libraries
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# ---------------------------------------------------------
# REGEX PATTERNS (removed company name patterns)
# ---------------------------------------------------------

ORG_RE = re.compile(r"\b(\d{9})\b")
ORG_IN_TEXT_RE = re.compile(
    r"(organisasjonsnummer|org\.?nr|org nr|orgnummer)[:\s]*?(\d{9})",
    flags=re.I
)

POST_CITY_RE = re.compile(
    r"(\d{4})\s+([A-ZÆØÅa-zæøå\-\s]{2,50})"
)

ADDRESS_RE = re.compile(
    r"([A-ZÆØÅa-zæøå.\-\s]{3,60}\s+\d{1,4}[A-Za-z]?)"
)

# Vehicle section keywords
VEHICLE_KEYWORDS = [
    "kjøretøyforsikring",
    "næringsbil",
    "varebil",
    "personbil",
    "registreringsnummer",
    "årsmodell",
    "arbeidsmaskin",
    "traktor",
    "uregistrert",
]

# ---------------------------------------------------------
# PDF TEXT EXTRACTION WITH OCR FALLBACK
# ---------------------------------------------------------

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Smart extraction with OCR fallback for image-based PDFs."""

    # Handle Streamlit UploadedFile objects
    if hasattr(pdf_bytes, 'read'):
        pdf_bytes = pdf_bytes.read()

    if not pdf_bytes:
        st.warning("⚠️ No PDF bytes provided")
        return ""

    st.write(f"📄 **Extracting from PDF** ({len(pdf_bytes)} bytes)")

    try:
        text = ""
        vehicle_section_found = False
        pages_after_vehicles = 0
        max_pages_to_read = 50
        pages_with_no_text = 0
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            st.success(f"✅ PDF: {total_pages} pages")
            st.info("🔍 Searching for vehicle section...")
            
            for i, page in enumerate(pdf.pages):
                if i >= max_pages_to_read:
                    st.warning(f"⚠️ Reached {max_pages_to_read} pages")
                    break
                
                # Try normal text extraction
                extracted = page.extract_text()
                
                # If no text, try OCR
                if not extracted or len(extracted.strip()) < 10:
                    pages_with_no_text += 1
                    
                    if OCR_AVAILABLE and pages_with_no_text >= 3 and i < 20:
                        if pages_with_no_text == 3:
                            st.warning("⚠️ **PDF is image-based - using OCR...**")
                        
                        try:
                            img = page.to_image(resolution=300)
                            pil_img = img.original
                            ocr_text = pytesseract.image_to_string(pil_img, lang='nor+eng')
                            
                            if ocr_text and len(ocr_text.strip()) > 10:
                                extracted = ocr_text
                                st.write(f"  ✓ Page {i+1}: {len(extracted)} chars (OCR)")
                        except Exception as ocr_err:
                            st.write(f"  · Page {i+1}: OCR failed")
                
                if extracted and len(extracted.strip()) > 10:
                    text += extracted + "\n"
                    
                    # Check for vehicle keywords
                    page_lower = extracted.lower()
                    has_vehicle_keywords = any(kw in page_lower for kw in VEHICLE_KEYWORDS)
                    
                    if has_vehicle_keywords:
                        if not vehicle_section_found:
                            st.success(f"🚗 Found vehicles at page {i+1}!")
                            vehicle_section_found = True
                        pages_after_vehicles = 0
                    else:
                        if vehicle_section_found:
                            pages_after_vehicles += 1
                            if pages_after_vehicles >= 5:
                                st.success(f"✅ Finished at page {i+1}")
                                break
        
        # Check if OCR needed but not available
        if pages_with_no_text >= total_pages * 0.5 and not OCR_AVAILABLE:
            st.error("❌ **PDF is image-based - OCR not installed!**")
            st.info("Install: pytesseract, pillow, tesseract-ocr")
        
        if text:
            st.success(f"✅ **Extracted {len(text)} characters**")
        else:
            st.error("❌ No text extracted!")
        
        return text

    except Exception as e:
        st.error(f"❌ Error: {e}")
        return ""

# ---------------------------------------------------------
# FIELD EXTRACTION (SIMPLIFIED - NO COMPANY NAME!)
# ---------------------------------------------------------

def extract_fields_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extract fields from PDF.
    NOTE: Company name comes from BRREG search, not PDF!
    """
    
    st.write("=" * 50)
    st.write("🔍 **PDF PARSER**")
    st.write("=" * 50)

    txt = extract_text_from_pdf(pdf_bytes)
    fields = {}

    if not txt:
        st.error("❌ No text extracted")
        return fields

    # IMPORTANT: Store full text for vehicle extraction
    fields["pdf_text"] = txt
    st.write(f"✓ Added 'pdf_text' ({len(txt)} chars)")

    # 1) Org number (optional - might find it in PDF)
    m = ORG_IN_TEXT_RE.search(txt)
    if m:
        fields["org_number"] = m.group(2)
        st.write(f"✓ Org number: {m.group(2)}")
    else:
        m2 = ORG_RE.search(txt)
        if m2:
            fields["org_number"] = m2.group(1)
            st.write(f"✓ Org number: {m2.group(1)}")

    # 2) Postal code + city (optional)
    mpc = POST_CITY_RE.search(txt)
    if mpc:
        fields["post_nr"] = mpc.group(1)
        fields["city"] = mpc.group(2).strip()
        st.write(f"✓ Postal: {mpc.group(1)} {mpc.group(2).strip()}")

    # 3) Address (optional)
    maddr = ADDRESS_RE.search(txt)
    if maddr:
        fields["address"] = maddr.group(1).strip()
        st.write(f"✓ Address: {maddr.group(1).strip()}")

    st.write("=" * 50)
    st.success(f"✅ Returning {len(fields)} fields")
    st.write(f"📝 Company name will come from BRREG, not PDF")
    st.write("=" * 50)

    return fields

# ---------------------------------------------------------
# PAGE VIEW
# ---------------------------------------------------------
def run():
    st.title("📄 PDF Parser Module")
    st.write("Extracts vehicle data from PDFs (with OCR support)")
    st.info("💡 Company name comes from BRREG search, not PDF!")
