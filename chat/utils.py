from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import Count, Q


def get_conversation(sender, recipient):
    """
    Retrieves all messages exchanged between the specified sender and recipient.
    The messages are ordered by the creation date.
    """
    MessageModel = apps.get_model("chat", "Message")
    conversation_filters = (Q(sender=sender) & Q(receiver=recipient)) | (
        Q(sender=recipient) & Q(receiver=sender)
    )
    conversation = MessageModel.objects.filter(conversation_filters).order_by("created")

    return conversation


def get_unseen_messages(user):
    """
    Retrieves a list of users who have sent unseen messages to the given user,
    along with the count of unseen messages for each sender.
    """
    MessageModel = apps.get_model("chat", "Message")
    unseen_message_counter = (
        MessageModel.objects.filter(receiver=user, seen=False)
        .values("sender")
        .annotate(unseen_count=Count("id"))
    )

    unseen_records = [
        {
            "user": User.objects.get(id=details.get("sender")),
            "unseen_count": details.get("unseen_count"),
        }
        for details in unseen_message_counter
    ]

    return unseen_records


def mark_messages_as_seen(sender, receiver):
    """
    Marks all unseen messages between the specified sender and receiver as 'seen'.
    """
    MessageModel = apps.get_model("chat", "Message")
    unseen_messages = MessageModel.objects.filter(
        sender=sender, receiver=receiver, seen=False
    )

    for message in unseen_messages:
        setattr(message, "seen", True)
        message.save()
