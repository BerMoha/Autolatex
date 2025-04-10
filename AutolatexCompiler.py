import streamlit as st
import requests
import tempfile

# === CONFIGURATION ===
st.set_page_config(page_title="Online LaTeX Compiler", layout="centered")

# Function to compile LaTeX file using QuickLaTeX API
def compile_latex_quicklatex(latex_content):
    url = "https://quicklatex.com/latex3.f"
    params = {
        "formula": latex_content,  # LaTeX content to be compiled
        "fsize": 50,  # Font size (optional)
        "out": "pdf",  # Output format
    }
    try:
        # Send LaTeX content to QuickLaTeX for compilation
        response = requests.get(url, params=params)
        response.raise_for_status()

        # Return the generated PDF or image URL
        pdf_url = response.text.split('url=')[-1]
        return pdf_url
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error during LaTeX compilation: {e}")
        return None

# === INTERFACE STREAMLIT ===

st.title("📄 Online LaTeX Compiler")

st.markdown("Upload a `.tex` or `.txt` file containing LaTeX structure to compile it into a PDF.")

uploaded_file = st.file_uploader("Choose a LaTeX file", type=["tex", "txt"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as tmp_file:
        tmp_file.write(uploaded_file.read())
        temp_path = tmp_file.name

    st.success(f"✅ File uploaded: {uploaded_file.name}")

    # Read the LaTeX content
    with open(temp_path, 'r') as f:
        latex_content = f.read()

    if st.button("🚀 Compile the file"):
        # Call QuickLaTeX API to compile the LaTeX content
        pdf_url = compile_latex_quicklatex(latex_content)
        if pdf_url:
            st.success("✅ PDF compiled successfully!")
            st.markdown(f"[⬇️ Download PDF]({pdf_url})")
        else:
            st.error("❌ LaTeX compilation failed. Please check your file and try again.")

