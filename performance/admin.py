from django.contrib import admin

from performance.models import (
    Evaluation,
    Poll,
    Questionnaire,
    UserEvaluation,
    Post,
    PostContent,
)

admin.site.register(Questionnaire)
admin.site.register(Evaluation)
admin.site.register(UserEvaluation)
admin.site.register(Poll)
admin.site.register(Post)
admin.site.register(PostContent)
