import streamlit as st
import subprocess
import os
import tempfile

st.set_page_config(page_title="📝 LaTeX Compiler", page_icon="📄")
st.title("📄 Compileur LaTeX en ligne")
st.markdown("Déposez un fichier `.tex` ou `.txt`, on s'occupe du reste !")

uploaded_file = st.file_uploader("📂 Glissez votre fichier ici :", type=["tex", "txt"])

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, uploaded_file.name)

        # Enregistrer le fichier sans tenter d'interpréter l'encodage
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())

        output_pdf = os.path.splitext(input_path)[0] + ".pdf"

        st.info("⏳ Compilation en cours...")
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", input_path],
                cwd=tmpdir,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'  # Ignore les erreurs d'encodage
            )

            if os.path.exists(output_pdf):
                with open(output_pdf, "rb") as f:
                    st.success("✅ Compilation réussie ! Voici votre PDF :")
                    st.download_button("📥 Télécharger le PDF", f, file_name="document.pdf")
            else:
                st.error("❌ La compilation a échoué. Aucun PDF généré.")
        except subprocess.CalledProcessError as e:
            st.error("❌ Erreur de compilation LaTeX.")
            st.code(e.stdout or "Aucune sortie.")
        except Exception as e:
            st.error("⚠️ Erreur inconnue.")
            st.code(str(e))


