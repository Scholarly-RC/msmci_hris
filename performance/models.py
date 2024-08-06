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
        
        if self.is_self_evaluation():
            return f"{year_and_quarter} - {self.evaluator.userdetails.get_user_fullname()} - SELF EVALUATION"
        
        return f"{year_and_quarter} - {self.user_evaluation.evaluatee.userdetails.get_user_fullname() if self.user_evaluation else ""} by {self.evaluator.userdetails.get_user_fullname()}"

    def is_self_evaluation(self) -> bool:
        return self.evaluator == self.user_evaluation.evaluatee

    def was_modified(self) -> bool:
        return self.questionnaire.content.get("questionnaire_content") != self.content_data
    
    def get_total_answered_questions_count(self):
        question_count = 0
        answered_question_count = 0
        for domain in self.content_data:
            domain_questions = domain.get("questions")
            question_count += len(domain_questions)
            for question in domain_questions:
                if question.get("rating"):
                    answered_question_count += 1
        return answered_question_count, question_count
    
    def is_all_questions_answered(self):
        answered_question_count, question_count = self.get_total_answered_questions_count()
        return answered_question_count == question_count
    
    def get_content_data_with_mean_per_domain(self):
        for domain in self.content_data:
            domain_questions = domain.get("questions")
            question_count = len(domain_questions)
            current_rating = 0
            for question in domain_questions:
                current_question_rating = question.get("rating")
                if current_question_rating:
                    current_rating += int(current_question_rating)
            current_mean = current_rating / question_count
            domain.update({"mean": current_mean})
        return self.content_data
    
    def get_overall_content_data_mean(self):
        content_data_with_mean = self.get_content_data_with_mean_per_domain()
        domain_count = len(content_data_with_mean)
        current_mean = 0
        for domain in content_data_with_mean:
            current_domain_mean = domain.get("mean")
            current_mean += current_domain_mean
        overall_mean = current_mean/domain_count
        return overall_mean

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
        return f"({self.evaluatee.userdetails.get_user_fullname()}) - ({self.year} - {self.quarter}) - {"Finalized" if self.is_finalized else "Pending"}"
    
    def get_year_and_quarter(self):
        quarter = self.Quarter(self.quarter).name.replace("_", " ")
        return f"{self.year} - {quarter}"
