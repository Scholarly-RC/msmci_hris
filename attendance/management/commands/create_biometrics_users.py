import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from zk import ZK
from zk.const import USER_DEFAULT

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Control the biometric registration of users."

    def handle(self, *args, **options):
        """
        Execute the command's main logic.

        Handles device connection, user registration, and error management with
        automatic retries. Runs continuously until successful execution or
        manual interruption.

        Args:
            *args: Additional positional arguments
            **options: Additional keyword arguments
        """
        conn = None
        while True:
            try:
                zk = ZK(
                    getattr(settings, "BIOMETRIC_DEVICE_IP"),
                    port=int(getattr(settings, "BIOMETRIC_DEVICE_PORT")),
                    timeout=5,
                )
                conn = zk.connect()

                if not conn:
                    logger.warning(
                        "Device connection failed, retrying in 10 seconds..."
                    )
                    time.sleep(10)
                    continue

                logger.info("Biometric device connected.")

                employees = []

                counter = 0

                for employee in employees:
                    conn.set_user(
                        uid=int(employee["id"]),
                        name=employee["fullname"],
                        privilege=USER_DEFAULT,
                        password="",
                        group_id="",
                        user_id=employee["id"],
                        card=0,
                    )
                    counter += 1

                self.stdout.write(
                    self.style.SUCCESS(f"Registered {counter} number of users.")
                )

            except Exception as e:
                logger.error(f"Capture error: {e}")
            finally:
                if conn:
                    try:
                        conn.disconnect()
                        break
                    except Exception as e:
                        logger.error(f"Error disconnecting from device: {e}")
