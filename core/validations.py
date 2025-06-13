import mimetypes

from django.apps import apps


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


def department_validation(department_data):
    """
    Validate new department data by checking for duplicate names and codes.
    Returns a list of error messages if any duplicates are found.
    """
    Department = apps.get_model("core", "Department")

    name_exists = Department.objects.filter(
        name__iexact=department_data.get("name")
    ).exists()
    code_exists = Department.objects.filter(
        code__iexact=department_data.get("code")
    ).exists()

    errors = []
    if name_exists:
        errors.append("Department name already exists.")
    if code_exists:
        errors.append("Department code already exists.")

    return errors


def edit_department_validation(department_data):
    """
    Validate department edit data by checking for duplicate names and codes,
    excluding the current department being edited.
    Returns a list of error messages if any duplicates are found.
    """
    Department = apps.get_model("core", "Department")

    name_exists = (
        Department.objects.filter(name__iexact=department_data.get("name"))
        .exclude(pk=department_data.get("department_id"))
        .exists()
    )
    code_exists = (
        Department.objects.filter(code__iexact=department_data.get("code"))
        .exclude(pk=department_data.get("department_id"))
        .exists()
    )

    errors = []
    if name_exists:
        errors.append("Department name already exists.")
    if code_exists:
        errors.append("Department code already exists.")

    return errors
