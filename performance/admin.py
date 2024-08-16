from django.contrib import admin

from performance.models import (
    Evaluation,
    Poll,
    Post,
    PostContent,
    Questionnaire,
    UserEvaluation,
)

admin.site.register(Questionnaire)
admin.site.register(Evaluation)
admin.site.register(UserEvaluation)
admin.site.register(Poll)
admin.site.register(Post)
admin.site.register(PostContent)
