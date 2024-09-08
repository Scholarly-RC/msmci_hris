from django.db import transaction


@transaction.atomic
def process_change_profile_picture(profile_picture, user_details):
    if user_details.profile_picture:
        user_details.profile_picture.delete()
    user_details.profile_picture = profile_picture
    user_details.save()
    return user_details
