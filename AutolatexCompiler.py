import requests
import streamlit as st

# QuickLaTeX API endpoint
url = "https://quicklatex.com/latex3.php"

# LaTeX code to be compiled
latex_code = """
\\documentclass{article}
\\begin{document}
Hello, this is a LaTeX document compiled via API!
\\end{document}
"""

# Prepare the POST request data
data = {
    'formula': latex_code,
    'output': 'pdf',  # You can also get other formats (e.g., png)
    'image': 'yes',  # Optional: set this if you want the result as an image
    'latex': 'yes'
}

# Send the POST request to QuickLaTeX API
response = requests.post(url, data=data)

if response.status_code == 200:
    # The response contains a URL to the generated PDF
    pdf_url = response.text.strip()  # The URL of the compiled PDF
    st.success("LaTeX compiled successfully!")
    st.markdown(f"[Download Compiled PDF]({pdf_url})")
    st.components.v1.iframe(pdf_url, height=600)  # Display the PDF in the Streamlit app
else:
    st.error(f"Failed to compile LaTeX. Status code: {response.status_code}")
    st.error(response.text)
