import sys
from pathlib import Path

def main():
    pdf_path = Path("g:/docs/TechmanStudios/sol/solKnowledge/working/Regarding_self_organizing_logos.pdf")
    out_path = Path("scratch/pdf_text.txt")
    
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for i, page in enumerate(reader.pages):
            text += f"--- Page {i+1} ---\n"
            text += page.extract_text() + "\n"
        out_path.write_text(text, encoding="utf-8")
        print("Success extracting text using pypdf")
    except Exception as e:
        print(f"Error using pypdf: {e}")
        # Try pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for i, page in enumerate(pdf.pages):
                    text += f"--- Page {i+1} ---\n"
                    text += page.extract_text() + "\n"
                out_path.write_text(text, encoding="utf-8")
                print("Success extracting text using pdfplumber")
        except Exception as e2:
            print(f"Error using pdfplumber: {e2}")

if __name__ == "__main__":
    main()
