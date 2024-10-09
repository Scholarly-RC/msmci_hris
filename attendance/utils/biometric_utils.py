from django.apps import apps
from django.utils.timezone import make_aware


def process_biometric_data_from_device(attendance_data):
    """
    Processes biometric data from a device, returning details including the user's biometric information,
    user ID, timestamp, and punch type.
    """
    user_id = attendance_data.user_id
    user_biometric_detail = _get_biometric_detail_from_device_user_id(user_id)

    punch = _get_punch_value(attendance_data.punch)

    timestamp = make_aware(attendance_data.timestamp)

    # TODO: Reserve for future usage
    status = attendance_data.status

    uid = attendance_data.uid

    return [
        user_biometric_detail,
        user_id,
        timestamp,
        punch,
    ]


def get_biometric_detail_from_user_id(user_id):
    """
    Retrieves biometric detail for a user based on their user ID.
    """
    biometric_detail_model = apps.get_model("core", "BiometricDetail")
    return biometric_detail_model.objects.filter(user__id=user_id).first()


def _get_biometric_detail_from_device_user_id(device_user_id):
    """
    Retrieves biometric detail based on a device-specific user ID.
    """
    biometric_detail_model = apps.get_model("core", "BiometricDetail")
    return biometric_detail_model.objects.filter(
        user_id_in_device=device_user_id
    ).first()


def _get_punch_value(value):
    """
    Maps a punch value from the device to a corresponding punch type.
    """
    attendance_record_model = apps.get_model("attendance", "AttendanceRecord")
    if value == 0:
        return attendance_record_model.Punch.TIME_IN.value

    if value == 1:
        return attendance_record_model.Punch.TIME_OUT.value

    if value == 4:
        return attendance_record_model.Punch.OVERTIME_IN.value

    if value == 5:
        return attendance_record_model.Punch.OVERTIME_OUT.value
