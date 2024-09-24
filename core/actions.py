from django.apps import apps
from django.db import transaction

from core.utils import get_dict_for_user_and_user_details, string_to_date


@transaction.atomic
def process_change_profile_picture(profile_picture, user_details):
    """
    Updates the user's profile picture, deleting the old one if it exists.
    """
    if user_details.profile_picture:
        user_details.profile_picture.delete()
    user_details.profile_picture = profile_picture
    user_details.save()
    return user_details


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

        return user_instance
    except Exception as error:
        raise error


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

    return [
        (user_details, user_details_created),
        (biometric_details, biometric_details_created),
    ]
