import streamlit as st
import pdfplumber
from io import BytesIO

# Try to import OCR libraries
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF with OCR support."""

    # Handle Streamlit UploadedFile objects
    if hasattr(pdf_bytes, 'read'):
        pdf_bytes = pdf_bytes.read()

    if not pdf_bytes:
        st.warning("⚠️ No PDF bytes provided")
        return ""

    st.write(f"📄 **Extracting from PDF** ({len(pdf_bytes)} bytes)")

    try:
        text = ""
        max_pages_to_read = 50
        pages_with_no_text = 0
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            st.success(f"✅ PDF: {total_pages} pages")
            
            for i, page in enumerate(pdf.pages):
                if i >= max_pages_to_read:
                    st.warning(f"⚠️ Stopped at {max_pages_to_read} pages")
                    break
                
                # Try normal text extraction
                extracted = page.extract_text()
                
                # If no text, try OCR immediately
                if not extracted or len(extracted.strip()) < 10:
                    pages_with_no_text += 1
                    
                    # Start OCR immediately if first page has no text
                    if OCR_AVAILABLE and pages_with_no_text >= 1 and i < 25:
                        if pages_with_no_text == 1:
                            st.warning("⚠️ **PDF is image-based - using OCR...**")
                        
                        try:
                            img = page.to_image(resolution=300)
                            pil_img = img.original
                            ocr_text = pytesseract.image_to_string(pil_img, lang='nor+eng')
                            
                            if ocr_text and len(ocr_text.strip()) > 10:
                                extracted = ocr_text
                                st.write(f"  ✓ Page {i+1}: {len(extracted)} chars (OCR)")
                        except Exception as ocr_err:
                            st.write(f"  · Page {i+1}: OCR failed - {ocr_err}")
                
                if extracted and len(extracted.strip()) > 10:
                    text += extracted + "\n"
        
        # Check if OCR needed but not available
        if pages_with_no_text >= total_pages * 0.5 and not OCR_AVAILABLE:
            st.error("❌ **PDF is image-based - OCR not installed!**")
            st.info("Install: `pip install pytesseract pillow` + tesseract-ocr")
        
        if text:
            st.success(f"✅ **Extracted {len(text)} characters**")
        else:
            st.error("❌ No text extracted!")
        
        return text

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return ""


def extract_fields_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extract ONLY pdf_text from PDF.
    All other fields (company name, address, etc.) come from BRREG.
    """
    
    st.write("=" * 50)
    st.write("🔍 **PDF PARSER**")
    st.write("=" * 50)

    txt = extract_text_from_pdf(pdf_bytes)
    fields = {}

    if not txt:
        st.error("❌ No text extracted")
        return fields

    # ONLY store the text
    fields["pdf_text"] = txt
    st.write(f"✓ Added 'pdf_text' ({len(txt)} chars)")

    st.write("=" * 50)
    st.success(f"✅ PDF text extracted successfully")
    st.info("💡 Company info comes from BRREG search")
    st.write("=" * 50)

    return fields


def run():
    st.title("📄 PDF Parser Module")
    st.write("Extracts text from PDFs (with OCR support)")
    st.info("💡 All company info comes from BRREG!")
