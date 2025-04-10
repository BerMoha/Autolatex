import streamlit as st
import requests

# === CONFIGURATION ===
st.set_page_config(page_title="AutoLaTeX Compiler", layout="centered")

# QuickLaTeX API endpoint
quicklatex_url = "https://quicklatex.com/latex3.php"

def compile_latex_file(latex_code):
    """
    Compiles LaTeX code remotely via the QuickLaTeX API.
    """
    data = {
        'formula': latex_code,  # The LaTeX code to compile
        'output': 'pdf',        # The output format: pdf
        'latex': 'yes',         # We are submitting LaTeX content
        'image': 'yes'          # Optional: if you want image output instead
    }

    # Send the LaTeX code to QuickLaTeX for compilation
    response = requests.post(quicklatex_url, data=data)

    if response.status_code == 200:
        # Extract the URL to the generated PDF from the API response
        pdf_url = response.text.strip()
        return pdf_url
    else:
        st.error(f"❌ Failed to compile LaTeX. Status code: {response.status_code}")
        st.error(response.text)
        return None

# === INTERFACE STREAMLIT ===
st.title("📄 AutoLaTeX Compiler")

st.markdown("Uploader un fichier `.tex` ou `.txt` contenant une structure LaTeX complète pour le compiler.")

uploaded_file = st.file_uploader("Choisir un fichier LaTeX", type=["tex", "txt"])

if uploaded_file is not None:
    # Read the content of the uploaded file
    file_content = uploaded_file.read().decode("utf-8")
    
    st.success(f"✅ Fichier enregistré : {uploaded_file.name}")

    if st.button("🚀 Compiler le fichier"):
        # Compile the LaTeX content remotely via QuickLaTeX API
        pdf_url = compile_latex_file(file_content)

        if pdf_url:
            st.success("✅ PDF généré avec succès!")
            st.markdown(f"[Télécharger le PDF]({pdf_url})")  # Provide a link to download the PDF
            st.components.v1.iframe(pdf_url, height=600)  # Display the PDF inline in the app
        else:
            st.error("❌ La compilation a échoué ou le fichier est vide.")
