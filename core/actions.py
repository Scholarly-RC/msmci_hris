import logging

from django.apps import apps
from django.db import transaction

from core.utils import (
    generate_username_from_employee_id,
    get_dict_for_user_and_user_details,
    string_to_date,
)
from performance.utils import extract_filename_and_extension

logger = logging.getLogger(__name__)


@transaction.atomic
def process_update_username(user_id=None):
    """
    Updates the usernames of users based on their employee ID.
    If a user_id is provided, updates the username for that specific user.
    If no user_id is provided, updates the usernames for all users in the system.
    """

    UserModel = apps.get_model("auth", "User")

    def _update_user_username(user_id):
        user = UserModel.objects.get(id=user_id)
        employee_id = user.userdetails.employee_number
        if employee_id:
            username = generate_username_from_employee_id(employee_id)
            user.username = username
            user.save()

    try:
        if not user_id:
            users = UserModel.objects.exclude(is_superuser=True)
            for user in users:
                _update_user_username(user_id=user.id)
        else:
            _update_user_username(user_id=user_id)
    except Exception:
        logger.error("Error occurred while updating usernames", exc_info=True)
        raise


@transaction.atomic
def process_change_profile_picture(profile_picture, user_details):
    """
    Updates the user's profile picture, deleting the old one if it exists.
    """
    try:
        if user_details.profile_picture:
            user_details.profile_picture.delete()
        user_details.profile_picture = profile_picture
        user_details.save()
        return user_details
    except Exception:
        logger.error("Error occurred while updating the profile picture", exc_info=True)
        raise


@transaction.atomic
def process_update_user_and_user_details(user_instance, querydict):
    """
    Updates a user instance and its associated user details based on the provided data.
    """
    try:
        user_payload, user_details_payload = get_dict_for_user_and_user_details(
            querydict
        )

        user_details = user_instance.userdetails

        for attr, value in user_payload.items():
            setattr(user_instance, attr, value)

        user_instance.save()

        date_fields = ["date_of_birth", "date_of_hiring"]

        processed_user_details = {
            attr: string_to_date(value) if attr in date_fields and value else value
            for attr, value in user_details_payload.items()
        }

        for attr, value in processed_user_details.items():
            if attr in date_fields and not value:
                value = None
            setattr(user_details, attr, value)

        user_details.save()

        process_update_username(user_id=user_instance.id)

        return user_instance, user_payload | user_details_payload
    except Exception:
        logger.error(
            "An error occurred while updating user and user details", exc_info=True
        )
        raise


@transaction.atomic
def process_get_or_create_intial_user_one_to_one_fields(user):
    """
    Retrieves or creates the initial one-to-one related fields for a user.
    """
    user_details, user_details_created = apps.get_model(
        "core", "UserDetails"
    ).objects.get_or_create(user=user)
    biometric_details, biometric_details_created = apps.get_model(
        "core", "BiometricDetail"
    ).objects.get_or_create(user=user)
    leave_credit_details, leave_credit_created = apps.get_model(
        "leave", "LeaveCredit"
    ).objects.get_or_create(user=user, defaults={"credits": 0, "used_credits": 0})

    return [
        (user_details, user_details_created),
        (biometric_details, biometric_details_created),
        (leave_credit_details, leave_credit_created),
    ]


@transaction.atomic
def process_add_personal_file(user, payload, file_data):
    """
    Adds a personal file with a selected category to the database.
    """
    PersonalFileModel = apps.get_model("core", "PersonalFile")
    try:
        file = file_data.get("personal_file")
        file_name, _ = extract_filename_and_extension(filename=file.name)
        category = payload.get("selected_category")
        personal_file_data = {
            "owner": user,
            "name": file_name,
            "file": file,
            "category": category,
        }
        if "academic_degree" in payload:
            personal_file_data["academic_degree"] = payload.get("academic_degree")

        if "year" in payload:
            personal_file_data["year"] = int(payload.get("year"))

        new_file = PersonalFileModel.objects.create(**personal_file_data)
        return new_file
    except Exception:
        logger.error("An error occurred while adding a Personal File", exc_info=True)
        raise


@transaction.atomic
def process_delete_personal_file(payload):
    """
    Deletes a personal file based on the provided file ID,
    removes the associated file from storage, and returns the file's category.
    If an error occurs during the process, it logs the exception and raises it.
    """
    PersonalFileModel = apps.get_model("core", "PersonalFile")
    file_id = payload.get("file")
    try:
        file = PersonalFileModel.objects.get(id=file_id)
        file_name = file.name
        category = file.category
        file.file.delete()
        file.delete()
        return category, file_name
    except Exception:
        logger.error("An error occurred while deleting a Personal File", exc_info=True)
        raise


@transaction.atomic
def process_add_department(payload):
    DepartmentModel = apps.get_model("core", "Department")
    name = payload.get("name")
    code = payload.get("code")
    department = DepartmentModel.objects.create(name=name, code=code)
    return department


@transaction.atomic
def process_edit_department(payload):
    DepartmentModel = apps.get_model("core", "Department")
    id = payload.get("department_id")
    name = payload.get("name")
    code = payload.get("code")
    department = DepartmentModel.objects.get(pk=id)
    department.name = name
    department.code = code
    department.save()

    return department


@transaction.atomic
def process_delete_department(payload):
    """ """
    DepartmentModel = apps.get_model("core", "Department")
    department_id = payload.get("department_id")
    try:
        department = DepartmentModel.objects.get(pk=department_id)
        department_name = department.name
        department.delete()
        return department_name
    except Exception:
        logger.error("An error occurred while deleting a Department", exc_info=True)
        raise


@transaction.atomic
def process_add_app_log_entry(user_id, details):
    AppLogModel = apps.get_model("core", "AppLog")
    UserModel = apps.get_model("auth", "User")
    new_log = AppLogModel.objects.create(
        user=UserModel.objects.get(id=user_id), details=details
    )
    return new_log
