from datetime import datetime

from django.apps import apps


def create_notification(
    content: str, date: datetime, sender_id: int, recipient_id: int, url: str = ""
):
    try:
        NotificationModel = apps.get_model("core", "Notification")
        UserModel = apps.get_model("auth", "User")
        sender = UserModel.objects.get(id=sender_id)
        recipient = UserModel.objects.get(id=recipient_id)

        NotificationModel.objects.create(
            content=content, date=date, sender=sender, recipient=recipient, url=url
        )
    except Exception as error:
        raise error


def mark_notification_read(notification):
    try:
        notification.read = True
        notification.save()
    except Exception as error:
        raise error


def user_has_unread_notification(user):
    return user.notifications.filter(read=False).exists()
