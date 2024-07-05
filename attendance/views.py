from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from zk import ZK, const

DEVICE_IP = "192.168.0.110"
zk = ZK(
    f"{DEVICE_IP}",
    port=4370,
    timeout=5,
    password=0,
    force_udp=False,
    ommit_ping=False,
)


@csrf_exempt
def get_attendance_request(request):
    return HttpResponse("OK")


@csrf_exempt
def attendance_cdata(request):
    if request.method == "POST":
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

    return HttpResponse("OK")
