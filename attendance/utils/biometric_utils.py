from django.apps import apps
from django.contrib.auth.models import User


def process_biometric_data_from_device(attendance_data):
    """
    STATUS:
        3 - pin
        15 - face recog
    """

    user_id = attendance_data.user_id
    user_biometric_detail = _get_user_from_biometric_device_user_id(user_id)

    current_user = None
    if user_biometric_detail:
        current_user = user_biometric_detail.user

    punch = _get_punch_value(attendance_data.punch)

    timestamp = attendance_data.timestamp

    # TODO: Reserve for future usage
    status = attendance_data.status

    uid = attendance_data.uid

    return [
        current_user,
        user_id,
        timestamp,
        punch,
    ]


def _get_user_from_biometric_device_user_id(user_id):
    biometric_detail_model = apps.get_model("core", "BiometricDetail")
    return biometric_detail_model.objects.filter(user_id_in_device=user_id).first()


def _get_punch_value(value):
    attendance_record_model = apps.get_model("attendance", "AttendanceRecord")
    if value == 0:
        return attendance_record_model.Punch.TIME_IN.value

    if value == 1:
        return attendance_record_model.Punch.TIME_OUT.value

    if value == 4:
        return attendance_record_model.Punch.OVERTIME_IN.value

    if value == 5:
        return attendance_record_model.Punch.OVERTIME_OUT.value
