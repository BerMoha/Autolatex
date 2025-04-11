import streamlit as st
import os
from pathlib import Path
import requests
import base64

# Page config
st.set_page_config(page_title="📝 Online LaTeX Compiler", layout="centered")

# Use Path for temporary storage
WORKING_DIR = Path("temp_latex")
WORKING_DIR.mkdir(exist_ok=True)

# Hypothetical backend API endpoint for LaTeX compilation (replace with actual service)
LATEX_API_URL = "https://api.example.com/compile-latex"  # Placeholder

def validate_latex_content(content: str) -> bool:
    """Check if content contains LaTeX-like structure."""
    return "\\documentclass" in content or "\\begin{document}" in content

def compile_latex_to_pdf(filename: str, content: str) -> tuple[bytes | None, str]:
    """Send LaTeX content to a backend API for PDF compilation."""
    if not validate_latex_content(content):
        return None, f"⏩ Skipped: {filename} (no valid LaTeX content detected)"

    try:
        # Send content to backend API
        response = requests.post(
            LATEX_API_URL,
            json={"content": content, "filename": filename},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success") and data.get("pdf"):
            # Decode base64 PDF from response
            pdf_data = base64.b64decode(data["pdf"])
            return pdf_data, "Compilation successful"
        else:
            return None, f"❌ Compilation failed: {data.get('error', 'Unknown error')}"
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {filename}"
    except requests.RequestException as e:
        return None, f"❌ Compilation error: {str(e)}"

def cleanup_temp_files() -> None:
    """Remove temporary files."""
    for file in WORKING_DIR.iterdir():
        try:
            file.unlink()
        except OSError:
            pass

# Streamlit UI
st.title("📝 Online LaTeX Compiler")
st.markdown(
    """
    Upload `.tex` or `.txt` files containing LaTeX code to generate PDFs.
    Preview your LaTeX in real-time below.
    """
)

# KaTeX for live preview (loaded via CDN in HTML)
st.markdown(
    """
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <div id="latex-preview"></div>
    <script>
        function renderLatex(content) {
            try {
                katex.render(content, document.getElementById('latex-preview'), {
                    throwOnError: false,
                    displayMode: true
                });
            } catch (e) {
                document.getElementById('latex-preview').innerHTML = 'Preview error: ' + e.message;
            }
        }
    </script>
    """,
    unsafe_allow_html=True
)

# File uploader
uploaded_files = st.file_uploader(
    "Drop your files here:",
    type=["tex", "txt"],
    accept_multiple_files=True,
    help="Maximum file size: 10MB"
)

if uploaded_files:
    for file in uploaded_files:
        if file.size > 10_000_000:  # 10MB limit
            st.error(f"❌ {file.name} exceeds 10MB limit")
            continue
        file_path = WORKING_DIR / file.name
        file_path.write_bytes(file.getbuffer())
    st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully.")

# Text area for editing and preview
st.subheader("Edit LaTeX Code")
selected_file = st.selectbox(
    "Select a file to edit or preview:",
    options=[f.name for f in WORKING_DIR.iterdir()] if any(WORKING_DIR.iterdir()) else ["No files uploaded"]
)

if selected_file != "No files uploaded":
    file_path = WORKING_DIR / selected_file
    with open(file_path, 'r', encoding='utf-8') as f:
        latex_content = f.read()
    
    edited_content = st.text_area(
        "Edit LaTeX code:",
        value=latex_content,
        height=300
    )
    
    # Update file with edited content
    if edited_content != latex_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(edited_content)
        st.success("✅ File updated with new content.")
    
    # Trigger KaTeX preview
    st.markdown(
        f"""
        <script>
            renderLatex({repr(edited_content)});
        </script>
        """,
        unsafe_allow_html=True
    )

if st.button("📄 Compile LaTeX Files", key="compile_button"):
    if not any(WORKING_DIR.glob("*.[tT][eE][xX]") or WORKING_DIR.glob("*.[tT][xX][tT]")):
        st.warning("⚠️ No files to compile.")
    else:
        with st.spinner("Compiling files..."):
            for file in WORKING_DIR.glob("*.[tT][eE][xX]") or WORKING_DIR.glob("*.[tT][xX][tT]"):
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                pdf_data, message = compile_latex_to_pdf(file.name, content)
                st.subheader(f"📂 {file.name}")
                
                if pdf_data:
                    st.success(f"✅ PDF generated for {file.name}")
                    st.download_button(
                        "📥 Download PDF",
                        pdf_data,
                        file_name=f"{file.stem}.pdf"
                    )
                else:
                    st.error(f"❌ Compilation failed: {message}")
            
            cleanup_temp_files()
            st.info("🧹 Cleanup of temporary files completed.")


