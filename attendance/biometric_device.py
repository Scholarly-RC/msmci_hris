from zk import ZK

from django.conf import settings
from attendance.actions import add_user_attendance_record

DEVICE_IP = settings.BIOMETRIC_DEVICE_IP


def get_biometric_data():
    conn = None
    zk = ZK(
        f"{DEVICE_IP}",
        port=4370,
        password=0,
        force_udp=False,
        ommit_ping=False,
    )
    try:
        # Connect to device
        conn = zk.connect()
        if conn is None:
            raise Exception("Failed to establish connection")

        # Disable device
        conn.disable_device()

        # Live capture with timeout handling
        try:
            for attendance in conn.live_capture():
                if attendance is None:
                    # Implement timeout logic here if any
                    pass
                else:
                    add_user_attendance_record(attendance_data=attendance)
                    break
        except Exception as error:
            print("Live capture operation timed out. {}".format(error))

        # Re-enable device
        conn.enable_device()

    except Exception as e:
        print("Process terminated: {}".format(e))
    finally:
        if conn:
            conn.disconnect()
