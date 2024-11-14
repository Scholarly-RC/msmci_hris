import uuid
from datetime import datetime

from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import Q


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
    user = User.objects.get(id=employee_id)

    if user.is_superuser:
        return "admin"

    user_details = user.userdetails
    if (
        user.first_name
        and user.last_name
        and user_details.middle_name
        and user_details.employee_number
    ):
        username = (
            user.first_name[:1]
            + user_details.middle_name[:1]
            + user.last_name[:1]
            + "_"
            + str(user_details.employee_number)
        )
        username = username.lower()
    else:
        username = user.email

    return username


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
        "gender",
    ]

    data = querydict.dict()

    user_dict = {field: data[field] for field in user_fields}
    user_details_dict = {
        field: data[field] if field in data else None for field in user_details_fields
    }

    if "department" in user_details_dict:
        department = user_details_dict["department"]
        if department:
            DepartmentModel = apps.get_model("core", "Department")
            selected_department = DepartmentModel.objects.get(id=department)
            user_details_dict["department"] = selected_department
        else:
            user_details_dict["department"] = None

    return user_dict, user_details_dict


def get_users_sorted_by_department(user_query: str = "", selected_department: int = 0):
    """
    Retrieves and sorts users by department and first name, excluding those with the HR role.
    Optionally filters users by a search query and/or a selected department.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    hr_role = UserDetailsModel.Role.HR.value

    users = User.objects.exclude(userdetails__role=hr_role).order_by(
        "userdetails__department__name", "first_name"
    )

    if selected_department:
        users = users.filter(userdetails__department=selected_department)

    if user_query:
        user_filter = (
            Q(first_name__icontains=user_query)
            | Q(last_name__icontains=user_query)
            | Q(email__icontains=user_query)
        )
        users = users.filter(user_filter)

    return users


def get_education_list():
    """
    Returns a list of educational attainment choices from the UserDetails model.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    return UserDetailsModel.EducationalAttainment.choices


def get_education_list_with_degrees_earned():
    """
    Returns a list of specific educational attainment values related to degrees earned.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    return [
        UserDetailsModel.EducationalAttainment.VOCATIONAL.value,
        UserDetailsModel.EducationalAttainment.BACHELOR.value,
        UserDetailsModel.EducationalAttainment.MASTER.value,
        UserDetailsModel.EducationalAttainment.DOCTORATE.value,
    ]


def get_civil_status_list():
    """
    Returns a list of civil status choices from the UserDetails model.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    return UserDetailsModel.CivilStatus.choices


def get_religion_list():
    """
    Returns a list of religion choices from the UserDetails model.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    return UserDetailsModel.Religion.choices


def get_role_list():
    """
    Returns a list of role choices from the UserDetails model.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    return UserDetailsModel.Role.choices


def get_gender_list():
    """
    Returns a list of gender choices from the UserDetails model.
    """
    UserDetailsModel = apps.get_model("core", "UserDetails")
    return UserDetailsModel.Gender.choices


def check_if_biometric_uid_exists(current_user, uid):
    """
    Checks if a biometric UID exists in the system for any user other than the current user.
    """
    BiometricDetailModel = apps.get_model("core", "BiometricDetail")
    return (
        BiometricDetailModel.objects.filter(user_id_in_device=uid)
        .exclude(user=current_user)
        .exists()
    )
