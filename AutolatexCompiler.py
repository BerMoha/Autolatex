
import streamlit as st
import os
import requests
import subprocess

st.title("Compile LaTeX from GitHub (Remote Only)")

repo_url = st.text_input("GitHub repository URL (e.g. https://github.com/owner/repo):")
tex_path = st.text_input("Path to .tex file in repo (e.g. main.tex or docs/paper.tex):")

if repo_url and tex_path:
    # Parse owner and repo from URL
    try:
        parts = repo_url.strip().rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]

        # Try main branch first, then master
        for branch in ["main", "master"]:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{tex_path}"
            r = requests.get(raw_url)
            if r.status_code == 200:
                break
        else:
            st.error(f"Could not fetch file from GitHub (tried 'main' and 'master' branches).")
            st.stop()

        st.success(f"Fetched {tex_path} from {owner}/{repo} [{branch}]")

        # Save .tex to /tmp
        local_tex = os.path.join("/tmp", os.path.basename(tex_path))
        with open(local_tex, "wb") as f:
            f.write(r.content)

        # Compile with pdflatex
        result = subprocess.run(
            ["/usr/bin/pdflatex", "-output-directory", "/tmp", local_tex],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            st.success("Compilation succeeded!")
            pdf_path = local_tex.replace(".tex", ".pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "Download PDF",
                        f,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf"
                    )
            else:
                st.error("PDF not found after compilation.")
        else:
            st.error("Compilation failed!")
            st.text_area("stdout", result.stdout, height=150)
            st.text_area("stderr", result.stderr, height=150)

    except Exception as e:
        st.error(f"Error: {str(e)}")
