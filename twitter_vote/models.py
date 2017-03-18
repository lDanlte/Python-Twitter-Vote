import uuid

from django.db import models

# Create your models here.


class User(models.Model):

    id = models.BigIntegerField(primary_key=True)
    user_name = models.TextField(max_length=32, null=False, editable=False)
    first_authorize_date = models.DateTimeField(null=False, editable=False, auto_now=True)
    profile_icon = models.TextField(max_length=255, null=False)
    lang = models.TextField(max_length=10, null=False)
    oauth_token = models.TextField(max_length=50, null=False)
    oauth_secret = models.TextField(max_length=50, null=False)
    remember_me_token = models.UUIDField(default=uuid.uuid4, db_index=True)


class Tweet(models.Model):

    id = models.BigIntegerField(primary_key=True)
    first_vote_date = models.DateTimeField(null=False, editable=False, auto_now=True)
    likes_count = models.IntegerField(null=False, default=0)
    dislikes_count = models.IntegerField(null=False, default=0)


class TweetVote(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE)
    vote_result = models.TextField(max_length=10, null=False)

    class Meta:
        unique_together = (("user", "tweet"))



