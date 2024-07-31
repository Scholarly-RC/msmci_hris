from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Questionnaire(models.Model):
    content = models.JSONField(_("Questionnaire Content"), null=True, blank=True)
    is_active = models.BooleanField(_("Is Questionnaire Active"), default=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Questionnaires"

    def __str__(self):
        return f"{self.content.get("questionnaire_name")} - ({self.content.get("questionnaire_code")})"


class Evaluation(models.Model):
    evaluator = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="evaluator_evaluations"
    )

    user_evaluation = models.ForeignKey(
        "UserEvaluation",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="evaluations",
    )

    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.RESTRICT)

    positive_feedback = models.TextField(
        _("Positive Feedback To Evaluatee"), null=True, blank=True
    )

    improvement_suggestion = models.TextField(
        _("Improvement Suggestion To Evaluatee"), null=True, blank=True
    )

    content_data = models.JSONField(_("Evaluation Content Data"), null=True, blank=True)

    date_submitted = models.DateTimeField(_("Evaluation Date"), null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Evaluations"

    def __str__(self):
        year_and_quarter = f"({self.user_evaluation.year} - {UserEvaluation.Quarter(self.user_evaluation.quarter).name})".replace("_", " ")
        return f"{year_and_quarter} - {self.user_evaluation.evaluatee.userdetails.get_user_fullname() if self.user_evaluation else ""} by {self.evaluator.userdetails.get_user_fullname()}"


class UserEvaluation(models.Model):
    class Quarter(models.TextChoices):
        FIRST_QUARTER = "FQ", _("First Quarter")
        SECOND_QUARTER = "SQ", _("Second Quarter")

    evaluatee = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="evaluatee_evaluations"
    )

    quarter = models.CharField(
        _("User Evaluaton Quarter"),
        max_length=2,
        choices=Quarter.choices,
        default=None,
        null=True,
        blank=True,
    )

    year = models.IntegerField(_("User Evaluation Year"), null=True, blank=True)

    is_finalized = models.BooleanField(_("Is User Evaluation Finalized"), default=False)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "User Evaluations"

    def __str__(self):
        return f"({self.evaluatee.userdetails.get_user_fullname()}) - {self.quarter} - {self.is_finalized}"
