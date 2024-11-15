import mimetypes


def password_validation(password, confirm_password):
    """
    Validates if the provided passwords match and meet the minimum length requirement.
    """
    errors = []

    if password != confirm_password:
        errors.append("Passwords does not match.")
        return errors

    if len(password) < 5:
        errors.append("Password must be at least 5 characters")

    return errors


def personal_file_validation(file_data):
    """
    Validates the 'personal_file' in the provided file data.
    Only image files and PDFs are allowed.
    """
    errors = []
    file = file_data.get("personal_file")

    mime_type, _ = mimetypes.guess_type(file.name)

    if not (
        mime_type and (mime_type.startswith("image") or mime_type == "application/pdf")
    ):
        errors.append("Only accepts PDFs and Image files.")

    return errors
