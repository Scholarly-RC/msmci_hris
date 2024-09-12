import uuid
from datetime import datetime

from django.apps import apps
from django.contrib.auth.models import User


def check_user_has_password(email):
    """
    Checks if a user with the given email has a usable password.
    """
    try:
        user = User.objects.get(email=email)
        if user.password and user.has_usable_password():
            return True
        return False
    except User.DoesNotExist:
        return False


def generate_username_from_employee_id(employee_id):
    """
    Generates a username based on the provided employee ID.
    """
    return f"emp-id-{employee_id}"


def string_to_date(string_date):
    """
    Converts a date string in 'YYYY-MM-DD' format to a datetime object.
    """
    return datetime.strptime(string_date, "%Y-%m-%d")


def date_to_string(date):
    """
    Converts a datetime object to a string in 'YYYY-MM-DD' format, or returns an empty string if the date is None.
    """
    return date.strftime("%Y-%m-%d") if date else ""


def profile_picture_validation(image):
    """
    Validates the profile picture by checking its file size and format.
    """
    if image.size > 1 * 1024 * 1024:
        return "File size should be under 1MB."

    if not image.name.lower().endswith((".jpg", ".jpeg", ".png")):
        return "File should be a JPEG or PNG image."

    return None


def get_user_profile_picture_directory_path(instance, filename):
    """
    Generates the directory path for storing a user's profile picture with a unique filename.
    """
    ext = filename.split(".")[1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"{instance.user.id}/profile_picture/{new_filename}"


def get_dict_for_user_and_user_details(querydict):
    """
    Extracts and organizes user and user details fields from a QueryDict.
    """
    user_fields = ["first_name", "last_name"]
    user_details_fields = [
        "middle_name",
        "address",
        "phone_number",
        "date_of_birth",
        "department",
        "rank",
        "date_of_hiring",
        "civil_status",
        "religion",
        "degrees_earned",
        "education",
        "employee_number",
        "role",
    ]

    data = querydict.dict()

    user_dict = {field: data[field] for field in user_fields}
    user_details_dict = {
        field: data[field] if field in data else None for field in user_details_fields
    }

    if "department" in user_details_dict:
        department = user_details_dict["department"]
        if department:
            department_model = apps.get_model("core", "Department")
            selected_department = department_model.objects.get(id=department)
            user_details_dict["department"] = selected_department
        else:
            user_details_dict["department"] = None

    return user_dict, user_details_dict


def get_users_sorted_by_department():
    """
    Retrieves users, excluding those with the HR role, and sorts them by department and first name.
    """
    user_details_model = apps.get_model("core", "UserDetails")
    hr_role = user_details_model.Role.HR.value

    users = User.objects.exclude(userdetails__role=hr_role).order_by(
        "userdetails__department__name", "first_name"
    )

    return users


def get_education_list():
    """
    Returns a list of educational attainment choices from the UserDetails model.
    """
    user_details_model = apps.get_model("core", "UserDetails")
    return user_details_model.EducationalAttainment.choices


def get_education_list_with_degrees_earned():
    """
    Returns a list of specific educational attainment values related to degrees earned.
    """
    user_details_model = apps.get_model("core", "UserDetails")
    return [
        user_details_model.EducationalAttainment.VOCATIONAL.value,
        user_details_model.EducationalAttainment.BACHELOR.value,
        user_details_model.EducationalAttainment.MASTER.value,
        user_details_model.EducationalAttainment.DOCTORATE.value,
    ]


def get_civil_status_list():
    """
    Returns a list of civil status choices from the UserDetails model.
    """
    user_details_model = apps.get_model("core", "UserDetails")
    return user_details_model.CivilStatus.choices


def get_religion_list():
    """
    Returns a list of religion choices from the UserDetails model.
    """
    user_details_model = apps.get_model("core", "UserDetails")
    return user_details_model.Religion.choices


def get_role_list():
    """
    Returns a list of role choices from the UserDetails model.
    """
    user_details_model = apps.get_model("core", "UserDetails")
    return user_details_model.Role.choices


def check_if_biometric_uid_exists(current_user, uid):
    """
    Checks if a biometric UID exists in the system for any user other than the current user.
    """
    biometric_detail_model = apps.get_model("core", "BiometricDetail")
    return (
        biometric_detail_model.objects.filter(user_id_in_device=uid)
        .exclude(user=current_user)
        .exists()
    )
