from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class Message(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="message_sender"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="message_receiver"
    )
    message = models.TextField(_("User Message"), null=True, blank=True)
    seen = models.BooleanField(_("Is User Message Seen"), default=False)
    created = models.DateField(auto_now_add=True, null=True, blank=True)
    updated = models.DateField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"{self.sender.get_full_name()} - {self.receiver.get_full_name()} ({self.created})"
