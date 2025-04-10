def compile_latex_online(latex_content):
    url = "https://quicklatex.com/latex3.f"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'formula': latex_content, 'fsize': '12', 'fcolor': '000000', 'bg': 'FFFFFF', 'mode': '0'}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.content  # PDF content
        else:
            st.error("❌ LaTeX compilation failed!")
            return None
    except Exception as e:
        st.error(f"❌ Error during API request: {e}")
        return None
