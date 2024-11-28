import logging
import os
import subprocess

from django.conf import settings
from filelock import FileLock

logger = logging.getLogger(__name__)


def convert_document_to_pdf(uploaded_file_instance, file_name):
    """
    Converts the provided document file (e.g., Word, Excel) to a PDF using LibreOffice in headless mode.
    The converted PDF is saved and linked to the provided file instance.

    This function uses a file lock to prevent concurrent conversions and ensures the conversion 
    completes successfully. If the conversion fails, it logs the error and raises an exception.
    """
    lock_file = "/tmp/pdf_conversion.lock"
    lock = FileLock(lock_file, timeout=600)

    try:
        lock.acquire()

        document_path = uploaded_file_instance.resource.path
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
            converted_file_path = output_pdf_path.split("media\\", 1)[-1]
            uploaded_file_instance.resource_pdf.name = converted_file_path
            uploaded_file_instance.save()
            print("PDF conversion successful.")
        else:
            logger.warning("PDF conversion failed: Output file not found.")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error during PDF conversion: {e.stderr}")
        raise

    except Exception as error:
        logger.exception("An error occurred during PDF conversion.")
        raise

    finally:
        lock.release()
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print("Lock file removed.")
