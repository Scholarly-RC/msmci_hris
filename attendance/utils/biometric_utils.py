from zk import ZK

DEVICE_IP = "192.168.0.110"
zk = ZK(
    f"{DEVICE_IP}",
    port=4370,
    timeout=5,
    password=0,
    force_udp=False,
    ommit_ping=False,
)


def get_biometric_data():
    try:
        # Connect to device
        conn = zk.connect()
        if conn is None:
            raise Exception("Failed to establish connection")

        # Disable device (if necessary)
        # conn.disable_device()

        # Live capture with timeout handling
        try:
            for attendance in conn.live_capture():
                if attendance is None:
                    # Implement timeout logic here
                    print("Capture timed out.")
                    break
                else:
                    print(attendance.punch)
                    break
        except TimeoutError:
            print("Live capture operation timed out.")

        # Re-enable device (if necessary)
        # conn.enable_device()
    except Exception as e:
        print("Process terminated: {}".format(e))
    finally:
        # Ensure the connection is closed properly
        if conn:
            try:
                conn.disconnect()
            except Exception as disconnect_error:
                print("Error during disconnection: {}".format(disconnect_error))
