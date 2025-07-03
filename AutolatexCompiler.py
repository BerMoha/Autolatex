
import streamlit as st
import os
import requests
import subprocess

st.title("GitHub LaTeX Compiler (Remote Only)")

repo_url = st.text_input("Enter GitHub repository URL (e.g. https://github.com/owner/repo):")
tex_path = st.text_input("Path to .tex file in repository (e.g. main.tex or docs/paper.tex):")

if repo_url and tex_path:
    # Parse owner and repo from URL
    try:
        parts = repo_url.strip().rstrip("/").split("/")
        owner, repo = parts[-2], parts[-1]

        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{tex_path}"
        r = requests.get(raw_url)
        if r.status_code == 404:
            # Try master branch for legacy repos
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{tex_path}"
            r = requests.get(raw_url)

        if r.status_code == 200:
            st.success(f"Fetched {tex_path} from {owner}/{repo}")
            # Save to /tmp
            local_tex = os.path.join("/tmp", os.path.basename(tex_path))
            with open(local_tex, "wb") as f:
                f.write(r.content)
            # Compile
            run = subprocess.run(
                ["/usr/bin/pdflatex", "-output-directory", "/tmp", local_tex],
                capture_output=True, text=True
            )
            if run.returncode == 0:
                st.success("Compilation succeeded!")
                pdf_path = local_tex.replace(".tex", ".pdf")
                with open(pdf_path, "rb") as f:
                    st.download_button("Download PDF", f, file_name=os.path.basename(pdf_path), mime="application/pdf")
            else:
                st.error("Compilation failed!")
                st.text_area("stdout", run.stdout, height=150)
                st.text_area("stderr", run.stderr, height=150)
        else:
            st.error(f"Could not fetch file from GitHub (HTTP {r.status_code}). Check your repo URL and path.")
    except Exception as e:
        st.error(f"Error: {str(e)}")
