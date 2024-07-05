from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import Count, Q


def get_chat_model(model_name):
    return apps.get_model("chat", f"{model_name}")


def get_conversation(sender, recipient):
    message_model = get_chat_model("Message")
    conversation_filters = (Q(sender=sender) & Q(receiver=recipient)) | (
        Q(sender=recipient) & Q(receiver=sender)
    )
    conversation = message_model.objects.filter(conversation_filters).order_by(
        "created"
    )

    return conversation


def get_unseen_messages(user):
    message_model = get_chat_model("Message")
    unseen_message_counter = (
        message_model.objects.filter(receiver=user, seen=False)
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
    message_model = get_chat_model("Message")
    unseen_messages = message_model.objects.filter(
        sender=sender, receiver=receiver, seen=False
    )

    for message in unseen_messages:
        setattr(message, "seen", True)
        message.save()
