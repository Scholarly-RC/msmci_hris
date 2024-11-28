import logging
from datetime import datetime

from django.apps import apps

logger = logging.getLogger(__name__)


def create_notification(
    content: str, date: datetime, sender_id: int, recipient_id: int, url: str = ""
):
    """
    Creates a new notification with the specified content, date, sender, recipient, and optional URL.
    If an error occurs during creation, it logs the exception and raises it.
    """
    try:
        NotificationModel = apps.get_model("core", "Notification")
        UserModel = apps.get_model("auth", "User")
        sender = UserModel.objects.get(id=sender_id)
        recipient = UserModel.objects.get(id=recipient_id)

        NotificationModel.objects.create(
            content=content, date=date, sender=sender, recipient=recipient, url=url
        )
    except Exception:
        logger.error("An error occurred while creating a notification", exc_info=True)
        raise


def mark_notification_read(notification):
    """
    Marks the specified notification as read and saves the change.
    If an error occurs, it logs the exception and raises it.
    """
    try:
        notification.read = True
        notification.save()
    except Exception:
        logger.error(
            "An error occurred while marking notification as read", exc_info=True
        )
        raise


def user_has_unread_notification(user):
    """
    Checks if the given user has any unread notifications.
    Returns True if there are unread notifications, otherwise False.
    """
    return user.notifications.filter(read=False).exists()
