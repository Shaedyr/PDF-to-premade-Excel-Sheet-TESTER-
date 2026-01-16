import streamlit as st
import app_modules.input as input_module


# Remove sidebar
st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed"
)

hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarNav"] {display: none;}
        [data-testid="stSidebarContent"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)


# Import only the modules you actually use
from app_modules import main_page
from app_modules import company_data
from app_modules import pdf_parser
from app_modules import summary
from app_modules import excel_filler
from app_modules import template_loader
from app_modules import download

# Sidebar page mapping
PAGES = {
    "🏠 Hovedside": main_page,
    "📄 Input-modul": input_modules,
    "🏢 Company Data": company_data,
    "📄 PDF Parser": pdf_parser,
    "📝 Summary Generator": summary,
    "📊 Excel Filler": excel_filler,
    "📁 Template Loader": template_loader,
    "📥 Download": download,
}

def main():
    st.set_page_config(page_title="PDF → Excel Automator", layout="wide")

    st.sidebar.title("Navigasjon")
    choice = st.sidebar.radio("Velg side:", list(PAGES.keys()))

    page = PAGES[choice]
    page.run()

if __name__ == "__main__":
    main()





