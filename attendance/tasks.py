import logging
import time

from django.apps import apps
from django.conf import settings
from django.utils.timezone import make_aware
from django_q.tasks import async_task
from zk import ZK

from attendance.utils.biometric_utils import process_biometric_data_from_device

DEVICE_IP = settings.BIOMETRIC_DEVICE_IP

logger = logging.getLogger(__name__)


def get_biometric_data():
    try:
        conn = None
        zk = ZK(f"{DEVICE_IP}", port=4370, timeout=5)
        conn = zk.connect()
        if conn is None:
            raise Exception("Failed to establish connection")

        try:
            start_time = time.time()
            for attendance in conn.live_capture():
                if time.time() - start_time > 30:
                    break
                if attendance:
                    async_task(
                        "attendance.tasks.add_user_attendance_record", attendance
                    )
                    print("Attendance successfully captured.")

        except Exception as error:
            logger.error("Live capture operation timed out: {}".format(error))
    except Exception as error:
        logger.error("Process terminated: {}".format(error))
    finally:
        if conn:
            conn.disconnect()


def add_user_attendance_record(attendance_data):
    """
    Creates a new attendance record for a user based on the provided biometric data from the device.
    """
    AttendanceRecordModel = apps.get_model("attendance", "AttendanceRecord")
    try:
        user_biometric_detail, user_id_from_device, timestamp, punch = (
            process_biometric_data_from_device(attendance_data)
        )

        attendance_record = AttendanceRecordModel.objects.create(
            user_biometric_detail=user_biometric_detail,
            user_id_from_device=user_id_from_device,
            timestamp=make_aware(timestamp),
            punch=punch,
        )

    except Exception:
        logger.error(
            "An error occurred while adding user attendance record", exc_info=True
        )
        raise
