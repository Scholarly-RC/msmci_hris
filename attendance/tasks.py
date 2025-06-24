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


def run_biometric_capture():
    """
    Continuously captures attendance data from biometric device
    and queues each record for processing using your existing function
    """
    while True:
        conn = None
        try:
            # Connect to device
            zk = ZK(
                getattr(settings, "BIOMETRIC_DEVICE_IP"),
                port=int(getattr(settings, "BIOMETRIC_DEVICE_PORT")),
                timeout=5,
            )
            conn = zk.connect()

            if not conn:
                logger.warning("Device connection failed, retrying in 10 seconds...")
                time.sleep(10)
                continue

            logger.info("Biometric device connected - starting live capture...")

            # Main capture loop
            for attendance in conn.live_capture():
                if attendance:
                    # Queue each record using your existing function
                    async_task(
                        "attendance.tasks.add_user_attendance_record",
                        attendance,
                    )

        except Exception as e:
            logger.error(f"Capture error: {e}")
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting from device: {e}")

        # Short delay before reconnecting if we got disconnected
        time.sleep(5)


def add_user_attendance_record(attendance_data):
    """
    Creates a new attendance record for a user based on biometric data from the device.
    The record includes user details, timestamp, and punch type (IN/OUT).
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
