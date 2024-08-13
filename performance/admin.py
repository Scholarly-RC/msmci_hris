from django.contrib import admin

from performance.models import Evaluation, Poll, Questionnaire, UserEvaluation

admin.site.register(Questionnaire)
admin.site.register(Evaluation)
admin.site.register(UserEvaluation)
admin.site.register(Poll)
