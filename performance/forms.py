from django.forms import ModelForm
from performance.models import Post, PostContent


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content"]


class PostContentForm(ModelForm):
    class Meta:
        model = PostContent
        fields = ["content"]
