import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import requests

# ---------- CONFIGURATION ----------
st.set_page_config(page_title="📄 Secure Online LaTeX Compiler", layout="centered")

# ---------- AUTHENTIFICATION ----------
# Exemple : un seul utilisateur pour commencer (Alice / motdepasse123)
names = ["Alice"]
usernames = ["alice"]
passwords = stauth.Hasher(["motdepasse123"]).generate()  # Hash le mot de passe

authenticator = stauth.Authenticate(
    names,
    usernames,
    passwords,
    "compiler_app",   # cookie name
    "abcdef",         # clé secrète pour le cookie
    cookie_expiry_days=1,
)

# Affichage du formulaire de login
name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"Bienvenue {name} 👋")

    # ---------- INTERFACE DE L'APP ----------
    st.title("📄 Secure Online LaTeX Compiler")
    st.markdown("Téléverse un fichier `.tex` ou `.txt` contenant du code LaTeX pour le compiler en PDF.")

    uploaded_file = st.file_uploader("Upload un fichier LaTeX", type=["tex", "txt"])

    if uploaded_file is not None:
        latex_content = uploaded_file.read().decode("utf-8")
        st.success(f"✅ Fichier reçu : {uploaded_file.name}")
        st.code(latex_content, language="latex")

        if st.button("🚀 Compiler"):
            with st.spinner("Compilation en cours..."):
                try:
                    response = requests.post(
                        "https://latexonline.cc/data",
                        files={"file": ("main.tex", latex_content)},
                        data={"compiler": "pdflatex"},
                    )
                    if response.status_code == 200 and response.headers["Content-Type"] == "application/pdf":
                        st.success("✅ PDF compilé avec succès !")
                        st.download_button(
                            label="⬇️ Télécharger le PDF",
                            data=response.content,
                            file_name="output.pdf",
                            mime="application/pdf",
                        )
                    else:
                        st.error("❌ Échec de la compilation. Vérifie ton code LaTeX.")
                except Exception as e:
                    st.error(f"❌ Erreur réseau ou serveur : {e}")

elif authentication_status is False:
    st.error("Nom d'utilisateur ou mot de passe incorrect.")

elif authentication_status is None:
    st.warning("Veuillez entrer vos identifiants.")



