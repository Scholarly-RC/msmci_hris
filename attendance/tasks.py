from datetime import timedelta
import logging
import time

from django.apps import apps
from django.conf import settings
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
    try:
        user_biometric_detail, _, timestamp, punch = process_biometric_data_from_device(
            attendance_data
        )

        user = user_biometric_detail.user

        user_daily_shift_schedule = user.daily_shift_schedules.filter(
            daily_shift_records__date=timestamp.date()
        ).first()
        if punch == "IN" and not user_daily_shift_schedule.clock_in:
            user_daily_shift_schedule.clock_in = timestamp
            user_daily_shift_schedule.save()
        elif punch == "OUT":
            yesterday_shift_schedule = user.daily_shift_schedules.filter(
                daily_shift_records__date=timestamp.date() - timedelta(days=1)
            ).first()
            if (
                yesterday_shift_schedule
                and yesterday_shift_schedule.shift.is_next_day_clock_out()
                and not yesterday_shift_schedule.clock_out
            ):
                yesterday_shift_schedule.clock_out = timestamp - timedelta(days=1)
                yesterday_shift_schedule.save()
            elif user_daily_shift_schedule.clock_out:
                user_daily_shift_schedule.clock_out = timestamp
                user_daily_shift_schedule.save()

    except Exception:
        logger.error(
            "An error occurred while adding user attendance record", exc_info=True
        )
        raise
