import os
import tempfile
from docx2pdf import convert
from django.core.files import File

def convert_word_to_pdf(new_shared_document, file_name):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf_path = temp_pdf.name

    try:
        docx_path = new_shared_document.document.path
        
        convert(docx_path, pdf_path)
        
        with open(pdf_path, "rb") as pdf_file:
            new_shared_document.document_pdf.save(f"{file_name}.pdf", File(pdf_file), save=False)
        
        new_shared_document.save()
    finally:
        # Ensure the temporary PDF file is removed
        if os.path.exists(pdf_path):
            os.remove(pdf_path)