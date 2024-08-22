import os
import subprocess

from django.conf import settings


def convert_document_to_pdf(uploaded_file_instance, file_name):
    try:
        document_path = uploaded_file_instance.document.path
        document_extension = uploaded_file_instance.get_file_extension()

        command = [
            settings.SOFFICE_PATH,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            os.path.dirname(document_path),
            document_path,
        ]

        subprocess.run(command, check=True, capture_output=True, text=True)

        output_pdf_path = document_path.replace(document_extension, ".pdf")

        if os.path.exists(output_pdf_path):
            uploaded_file_instance.document_pdf.name = output_pdf_path
            uploaded_file_instance.save()

    except subprocess.CalledProcessError as e:
        print(f"Error during PDF conversion: {e.stderr}")
        raise e

    except Exception as error:
        print(f"An error occurred: {error}")
        raise error
