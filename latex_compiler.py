import os
import subprocess
import shutil

# Directory containing .tex and .txt files
folder = r"C:\Users\BERKANIMO\Desktop\Autolatex"
os.makedirs(folder, exist_ok=True)

def has_latex_preamble(filepath):
    """Check if a file contains LaTeX preamble keywords."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return '\\documentclass' in content and '\\begin{document}' in content
    except Exception as e:
        print(f"⚠️ Could not read {filepath}: {e}")
        return False

def compile_latex_file(filename):
    """Compile LaTeX from .tex or valid .txt file."""
    if not filename.lower().endswith(('.tex', '.txt')):
        return

    input_path = os.path.join(folder, filename)

    # Skip .txt files without LaTeX preamble
    if filename.lower().endswith('.txt') and not has_latex_preamble(input_path):
        print(f"⏩ Skipping {filename} (no LaTeX preamble detected)")
        return

    # Rename .txt to .tex temporarily for compilation
    original_path = input_path
    if filename.lower().endswith('.txt'):
        tex_name = filename.replace('.txt', '.tex')
        input_path = os.path.join(folder, tex_name)
        os.rename(original_path, input_path)
        filename = tex_name

    output_pdf = os.path.join(folder, os.path.splitext(filename)[0] + ".pdf")

    print("="*50)
    print(f"📄 Processing file: {filename}")
    print(f"Full path: {input_path}")
    print("="*50)

    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        return

    try:
        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={folder}",
                input_path
            ],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ PDF created: {output_pdf}")
        if result.stdout:
            print(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Compilation failed for {filename}")
        print(f"Error code: {e.returncode}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        if e.stdout:
            print(f"Output: {e.stdout}")
    except FileNotFoundError:
        print("❌ pdflatex executable not found in system PATH")
        print("Please install TeX Live or MiKTeX and add pdflatex to PATH")

def process_files():
    """Process all .tex and valid .txt files in the directory."""
    if not shutil.which("pdflatex"):
        print("❌ 'pdflatex' is not installed or not in the system PATH.")
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith(('.tex', '.txt'))]
    if not files:
        print(f"⚠️ No .tex or .txt files found in {folder}")
        return

    print(f"Found {len(files)} file(s): {files}")
    for filename in files:
        compile_latex_file(filename)

def cleanup_auxiliary_files():
    """Remove auxiliary LaTeX files."""
    auxiliary_extensions = [".aux", ".log", ".out", ".toc"]
    for filename in os.listdir(folder):
        if any(filename.endswith(ext) for ext in auxiliary_extensions):
            try:
                os.remove(os.path.join(folder, filename))
            except Exception as e:
                print(f"⚠️ Error removing {filename}: {e}")

if __name__ == "__main__":
    print("Starting LaTeX compilation...")
    process_files()
    print("Cleaning up auxiliary files...")
    cleanup_auxiliary_files()
    print("Process complete!")
