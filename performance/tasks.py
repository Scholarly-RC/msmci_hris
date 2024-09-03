import os
import subprocess

from django.conf import settings
from filelock import FileLock


def convert_document_to_pdf(uploaded_file_instance, file_name):
    lock_file = "/tmp/pdf_conversion.lock"
    lock = FileLock(lock_file, timeout=600)

    try:
        lock.acquire()
        print("Lock acquired.")

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

        print(f"Running command: {' '.join(command)}")

        subprocess.run(command, check=True, capture_output=True, text=True)

        output_pdf_path = document_path.replace(document_extension, ".pdf")

        if os.path.exists(output_pdf_path):
            uploaded_file_instance.resource_pdf.name = output_pdf_path
            uploaded_file_instance.save()
            print("PDF conversion successful.")
        else:
            print("PDF conversion failed: Output file not found.")

    except subprocess.CalledProcessError as e:
        print(f"Error during PDF conversion: {e.stderr}")
        raise

    except Exception as error:
        print(f"An error occurred: {error}")
        raise

    finally:
        lock.release()
        print("Lock released.")

        if os.path.exists(lock_file):
            os.remove(lock_file)
            print("Lock file removed.")
