import os
import subprocess
import shutil

# Directory containing .tex or .txt files
folder = r"C:\Users\BERKANIMO\Desktop\Autolatex"
os.makedirs(folder, exist_ok=True)

def compile_latex_file(filename):
    """Compile a .tex or .txt file to PDF using pdflatex."""
    if not filename.lower().endswith((".tex", ".txt")):
        return

    input_path = os.path.join(folder, filename)
    output_pdf = os.path.join(folder, os.path.splitext(filename)[0] + ".pdf")

    print("="*50)
    print(f"📄 Processing file: {filename}")
    print(f"Full path: {input_path}")
    print("="*50)

    # Check if file exists
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
    """Process all .tex and .txt files in the directory."""
    if not shutil.which("pdflatex"):
        print("❌ 'pdflatex' is not installed or not in the system PATH.")
        print("Please install TeX Live or MiKTeX and add pdflatex to PATH.")
        return

    # Include both .tex and .txt files
    tex_files = [
        f for f in os.listdir(folder)
        if f.lower().endswith((".tex", ".txt"))
    ]

    if not tex_files:
        print(f"⚠️ No .tex or .txt files found in {folder}")
        return

    print(f"Found {len(tex_files)} LaTeX file(s): {tex_files}")
    for filename in tex_files:
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

