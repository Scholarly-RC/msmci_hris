from django.contrib import admin

from performance.models import (
    Evaluation,
    Poll,
    Post,
    PostContent,
    Questionnaire,
    SharedResource,
    UserEvaluation,
)

admin.site.register(Evaluation)
admin.site.register(Poll)
admin.site.register(Post)
admin.site.register(PostContent)
admin.site.register(Questionnaire)
admin.site.register(SharedResource)
admin.site.register(UserEvaluation)
