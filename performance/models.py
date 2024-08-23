import json
import mimetypes

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _
from prose.fields import RichTextField
from prose.models import AbstractDocument

from performance.utils import (
    extract_filename_and_extension,
    get_list_mean,
    get_question_rating_mean_from_evaluations,
    get_shared_resources_directory_path,
    get_user_questionnaire,
)


# Create your models here.
class Questionnaire(models.Model):
    content = models.JSONField(_("Questionnaire Content"), null=True, blank=True)
    is_active = models.BooleanField(_("Is Questionnaire Active"), default=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Questionnaires"

    def __str__(self):
        return f"{self.content.get('questionnaire_name')} - ({self.content.get('questionnaire_code')})"


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
        year_and_quarter = f"({self.user_evaluation.year} - {UserEvaluation.Quarter(self.user_evaluation.quarter).name})".replace(
            "_", " "
        )

        if self.is_self_evaluation():
            return f"{year_and_quarter} - {self.evaluator.userdetails.get_user_fullname()} - SELF EVALUATION"

        return f"{year_and_quarter} - {self.user_evaluation.evaluatee.userdetails.get_user_fullname() if self.user_evaluation else ''} by {self.evaluator.userdetails.get_user_fullname()}"

    def is_self_evaluation(self) -> bool:
        return self.evaluator == self.user_evaluation.evaluatee

    def is_modified(self) -> bool:
        return (
            self.questionnaire.content.get("questionnaire_content") != self.content_data
        )

    def get_total_answered_questions_count(self):
        question_count = 0
        answered_question_count = 0
        for domain in self.content_data:
            domain_questions = domain.get("questions")
            question_count += len(domain_questions)
            for question in domain_questions:
                if question.get("rating"):
                    answered_question_count += 1

        if not self.is_self_evaluation():
            question_count += 2
            if bool(self.positive_feedback and self.positive_feedback.strip()):
                answered_question_count += 1
            if bool(
                self.improvement_suggestion and self.improvement_suggestion.strip()
            ):
                answered_question_count += 1

        return answered_question_count, question_count

    def is_all_questions_answered(self) -> bool:
        answered_question_count, question_count = (
            self.get_total_answered_questions_count()
        )
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
        overall_mean = current_mean / domain_count
        return overall_mean

    def get_specific_rating(self, domain_number: str, indicator_number: str):
        for domain in self.content_data:
            current_domain_number = domain.get("domain_number")
            if current_domain_number == domain_number:
                current_domain_questions = domain.get("questions")
                for question in current_domain_questions:
                    if question.get("indicator_number") == indicator_number:
                        return question.get("rating")

    def is_submitted(self) -> bool:
        return self.date_submitted is not None

    def revert_submission(self):
        self.date_submitted = None
        self.save()

    def reset_evaluation(self):
        questionnaire = self.questionnaire
        questionnaire_content_data = questionnaire.content.get("questionnaire_content")
        self.content_data = questionnaire_content_data
        self.positive_feedback = None
        self.improvement_suggestion = None

        self.revert_submission()


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
        return f"({self.evaluatee.userdetails.get_user_fullname()}) - ({self.year} - {self.quarter}) - {'Finalized' if self.is_finalized else 'Pending'}"

    def get_year_and_quarter(self):
        quarter = self.Quarter(self.quarter).name.replace("_", " ")
        return f"{self.year} - {quarter}"

    def get_questionnaire_content_data_with_self_and_peer_rating_mean(self):
        questionnaire = get_user_questionnaire(self.evaluatee)
        questionnaire_content = questionnaire.content.get("questionnaire_content")
        self_evaluation = self.evaluations.filter(evaluator=self.evaluatee)
        peer_evaluations = self.evaluations.exclude(evaluator=self.evaluatee)

        for domain in questionnaire_content:
            self_eval = []
            peer_eval = []
            current_domain_number = domain.get("domain_number")
            current_questions = domain.get("questions")
            for question in current_questions:
                current_indicator_number = question.get("indicator_number")
                question["self_rating"] = get_question_rating_mean_from_evaluations(
                    self_evaluation, current_domain_number, current_indicator_number
                )
                self_eval.append(question["self_rating"])
                question["peer_rating"] = get_question_rating_mean_from_evaluations(
                    peer_evaluations, current_domain_number, current_indicator_number
                )
                peer_eval.append(question["peer_rating"])
                del question["rating"]
            domain["self_rating_mean"] = get_list_mean(self_eval)
            domain["peer_rating_mean"] = get_list_mean(peer_eval)

        return questionnaire_content

    def get_overall_self_and_peer_rating_mean(self):
        self_eval = []
        peer_eval = []
        questionnaire_content_data = (
            self.get_questionnaire_content_data_with_self_and_peer_rating_mean()
        )
        for data in questionnaire_content_data:
            self_rating_mean = data.get("self_rating_mean")
            peer_rating_mean = data.get("peer_rating_mean")
            self_eval.append(self_rating_mean)
            peer_eval.append(peer_rating_mean)
        self_eval_overall_mean = get_list_mean(self_eval)
        peer_eval_overall_mean = get_list_mean(peer_eval)

        return self_eval_overall_mean, peer_eval_overall_mean

    def get_evaluator_comments(self):
        evaluations = self.evaluations.exclude(evaluator=self.evaluatee)
        positive_feedback_list = []
        improvement_suggestion_list = []

        for evaluation in evaluations:
            if evaluation.positive_feedback:
                positive_feedback_list.append(evaluation.positive_feedback)

            if evaluation.improvement_suggestion:
                improvement_suggestion_list.append(evaluation.improvement_suggestion)

        return positive_feedback_list, improvement_suggestion_list

    def show_peer_evaluations(self) -> bool:
        peer_evaluations = self.evaluations.exclude(evaluator=self.evaluatee)
        for peer_evaluation in peer_evaluations:
            if not peer_evaluation.is_submitted():
                return False
        return True


class Poll(models.Model):
    name = models.CharField(
        _("Poll Name"),
        max_length=500,
        null=True,
        blank=True,
    )

    description = models.TextField(
        _("Poll Description"),
        null=True,
        blank=True,
    )

    data = models.JSONField(_("Poll Data"), null=True, blank=True, default=list)

    multiple_selection = models.BooleanField(
        _("Allow Multiple Poll Selection"), default=False
    )

    in_progress = models.BooleanField(_("Is Poll In Progress"), default=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Polls"

    def __str__(self):
        return f"{self.name} - {'IN-PROGRESS' if self.in_progress else 'ENDED'}"

    def get_number_of_choices(self) -> int:
        return len(self.data)

    def get_choices(self):
        poll_stats = self.get_stats_for_donut_chart()
        poll_stats = json.loads(poll_stats)
        choices = poll_stats.get("labels", [])
        return choices

    def has_choices(self):
        choices = self.get_choices()
        choices_count = len(choices)
        return choices_count > 0

    def get_stats_for_donut_chart(self):
        labels = []
        counts = []
        colors = []

        for data_item in self.data:
            key = next(iter(data_item))
            value = data_item[key]

            labels.append(str(key))
            counts.append(len(value.get("voters", [])))
            colors.append(str(value.get("color")))

        stats = {"labels": labels, "counts": counts, "colors": colors}

        json_stats = json.dumps(stats)

        return json_stats

    def is_poll(self):
        return True


class PostContent(AbstractDocument):
    pass

    class Meta:
        verbose_name_plural = "Post Contents"

    def __str__(self):
        return f"Content of Post #{self.post.id}"


class Post(models.Model):
    title = models.CharField(
        _("Post Title"),
        max_length=500,
        null=True,
        blank=True,
    )

    description = models.TextField(
        _("Post Description"),
        null=True,
        blank=True,
    )

    content = RichTextField(null=True, blank=True)

    body = models.OneToOneField(
        PostContent, on_delete=models.CASCADE, null=True, blank=True
    )

    is_active = models.BooleanField(_("Is Post Active"), default=True)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Posts"

    def __str__(self):
        return f"{self.title}"

    def is_post(self):
        return True


class SharedResource(models.Model):
    uploader = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="uploaded_resources"
    )
    shared_to = models.ManyToManyField(
        User, related_name="shared_to_resources", blank=True
    )

    resource_name = models.CharField(
        _("Resource Name"),
        max_length=500,
        null=True,
        blank=True,
    )

    resource = models.FileField(
        _("Resource"),
        null=True,
        blank=True,
        upload_to=get_shared_resources_directory_path,
    )

    resource_pdf = models.FileField(
        _("Resource as PDF"),
        null=True,
        blank=True,
        upload_to=get_shared_resources_directory_path,
    )

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Shared Resources"

    def __str__(self):
        return f"{self.uploader.get_full_name()} - {self.resource_name}"

    def get_file_extension(self):
        _, ext = extract_filename_and_extension(self.resource.name)
        return ext

    def is_resource_pdf(self):
        return self.get_file_extension() == ".pdf"

    def is_resource_excel(self):
        return self.get_file_extension() in {".xls", ".xlsx"}

    def is_resource_word(self):
        return self.get_file_extension() in {".doc", ".docx"}

    def is_resource_powerpoint(self):
        return self.get_file_extension() in {".ppt", ".pptx"}

    def is_resource_video(self):
        mime_type, _ = mimetypes.guess_type(self.resource.name)
        return mime_type and mime_type.startswith("video")

    def is_resource_image(self):
        mime_type, _ = mimetypes.guess_type(self.resource.name)
        return mime_type and mime_type.startswith("image")

    def is_resource_media(self):
        return self.is_resource_image() or self.is_resource_video()

    def get_resource_url_for_preview(self):
        if self.is_resource_pdf():
            return self.resource.url
        return self.resource_pdf.url

    def ready_to_view(self):
        if self.is_resource_pdf():
            return True
        return self.resource_pdf
