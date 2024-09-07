import uuid
from datetime import datetime

from django.apps import apps
from django.contrib.auth.models import User


def check_user_has_password(email):
    try:
        user = User.objects.get(email=email)
        if user.password and user.has_usable_password():
            return True
        return False
    except User.DoesNotExist:
        return False


def generate_username_from_employee_id(employee_id):
    return f"emp-id-{employee_id}"


def password_validation(password, confirm_password):
    errors = []

    if password != confirm_password:
        errors.append("Passwords does not match.")
        return errors

    if len(password) < 5:
        errors.append("Password must be at least 5 characters")

    return errors


def string_to_date(string_date):
    return datetime.strptime(string_date, "%Y-%m-%d")


def date_to_string(date):
    return date.strftime("%Y-%m-%d") if date else ""


def profile_picture_validation(image):
    # Check file size (max 1MB)
    if image.size > 1 * 1024 * 1024:
        return "File size should be under 1MB."

    # Check file type
    if not image.name.lower().endswith((".jpg", ".jpeg", ".png")):
        return "File should be a JPEG or PNG image."

    return None


def get_user_profile_picture_directory_path(instance, filename):
    ext = filename.split(".")[1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"{instance.user.id}/profile_picture/{new_filename}"


def get_dict_for_user_and_user_details(querydict):
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


def update_user_and_user_details(user_instance, querydict):
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

        return user_instance
    except Exception as e:
        raise e


def get_education_list():
    user_details_model = apps.get_model("core", "UserDetails")
    return user_details_model.EducationalAttainment.choices


def get_education_list_with_degrees_earned():
    user_details_model = apps.get_model("core", "UserDetails")
    return [
        user_details_model.EducationalAttainment.VOCATIONAL.value,
        user_details_model.EducationalAttainment.BACHELOR.value,
        user_details_model.EducationalAttainment.MASTER.value,
        user_details_model.EducationalAttainment.DOCTORATE.value,
    ]


def get_civil_status_list():
    user_details_model = apps.get_model("core", "UserDetails")
    return user_details_model.CivilStatus.choices


def get_religion_list():
    user_details_model = apps.get_model("core", "UserDetails")
    return user_details_model.Religion.choices


def get_role_list():
    user_details_model = apps.get_model("core", "UserDetails")
    return user_details_model.Role.choices


def get_or_create_intial_user_one_to_one_fields(user):
    user_details, user_details_created = apps.get_model(
        "core", "UserDetails"
    ).objects.get_or_create(user=user)
    biometric_details, biometric_details_created = apps.get_model(
        "core", "BiometricDetail"
    ).objects.get_or_create(user=user)

    return [
        (user_details, user_details_created),
        (biometric_details, biometric_details_created),
    ]


def check_if_biometric_uid_exists(current_user, uid):
    biometric_detail_model = apps.get_model("core", "BiometricDetail")
    return (
        biometric_detail_model.objects.filter(user_id_in_device=uid)
        .exclude(user=current_user)
        .exists()
    )
