import streamlit as st
import requests

st.set_page_config(page_title="📄 Online LaTeX Compiler", layout="centered")

def compile_with_latexonline(latex_content):
    try:
        response = requests.post(
            "https://latexonline.cc/data",
            files={"file": ("main.tex", latex_content)},
            data={"compiler": "pdflatex"},
        )
        if response.status_code == 200 and response.headers["Content-Type"] == "application/pdf":
            return response.content
        else:
            st.error("⚠️ Compilation failed. Please check your LaTeX code.")
            return None
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None

st.title("📄 Online LaTeX Compiler")

st.markdown("Upload a `.tex` or `.txt` file containing full LaTeX code (`\\documentclass`...) and compile it into a PDF.")

uploaded_file = st.file_uploader("Upload a LaTeX file", type=["tex", "txt"])

if uploaded_file is not None:
    latex_content = uploaded_file.read().decode("utf-8")
    st.success(f"✅ File uploaded: {uploaded_file.name}")
    st.code(latex_content, language="latex")

    if st.button("🚀 Compile LaTeX"):
        pdf_data = compile_with_latexonline(latex_content)
        if pdf_data:
            st.success("✅ PDF compiled successfully!")
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_data,
                file_name="output.pdf",
                mime="application/pdf"
            )


