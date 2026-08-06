import io
import pandas as pd

def parse_file(uploaded_file):
    file_type = uploaded_file.name.split(".")[-1].lower()
    text = ""
    try:
        if file_type == "pdf":
            import pdfplumber
            with pdfplumber.open(io.BytesIO(uploaded_file.getvalue())) as pdf:
                text = "\n".join([p.extract_text() or "" for p in pdf.pages[:30]])
        elif file_type == "docx":
            from docx import Document
            doc = Document(io.BytesIO(uploaded_file.getvalue()))
            text = "\n".join([p.text for p in doc.paragraphs])
        elif file_type in ["csv", "xlsx"]:
            df = pd.read_csv(uploaded_file) if file_type == "csv" else pd.read_excel(uploaded_file)
            text = df.head(100).to_string()
        else:
            text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    except Exception as e:
        text = f"Error reading {uploaded_file.name}: {str(e)}"
    return {"name": uploaded_file.name, "text": text}
