from uuid import uuid4

from django.db import transaction
from django.http.response import HttpResponse, JsonResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from urllib import parse
from django.conf import settings
import oauth2 as oauth

from twitter_vote.decorators import allowed_methods, auth_is_required
from .models import User, Tweet, TweetVote
import json


consumer = oauth.Consumer(settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)
client = oauth.Client(consumer)


@allowed_methods(methods=["GET"])
def authorize(request):
    resp, content = client.request("https://api.twitter.com/oauth/request_token", method="POST")
    if resp["status"] != "200":
        raise Exception("Error while twitter request " + resp["status"])

    resp_content = dict(parse.parse_qsl(content.decode("UTF-8")))

    print(resp_content)
    request.session["oauth_token"] = resp_content["oauth_token"]
    request.session["oauth_token_secret"] = resp_content["oauth_token_secret"]
    return HttpResponseRedirect("https://api.twitter.com/oauth/authorize?oauth_token=%s" % resp_content["oauth_token"])


@allowed_methods(methods=["GET"])
def authorize_callback(request):
    print(request.GET)
    token = oauth.Token(request.session["oauth_token"], request.session["oauth_token_secret"])
    token.set_verifier(request.GET["oauth_verifier"])
    new_client = oauth.Client(consumer, token)
    resp, content = new_client.request("https://api.twitter.com/oauth/access_token", method="POST")
    print(content)

    if resp["status"] != "200":
        raise Exception("Error while twitter request " + resp["status"])

    new_tokens = dict(parse.parse_qsl(content.decode("UTF-8")))

    print(new_tokens)

    del request.session["oauth_token"]
    del request.session["oauth_token_secret"]

    original_token = oauth.Token(new_tokens["oauth_token"], new_tokens["oauth_token_secret"])
    original_client = oauth.Client(consumer, original_token)

    resp, content = original_client.request(
        "https://api.twitter.com/1.1/account/verify_credentials.json?skip_status=true",
        method="GET"
    )
    if resp["status"] != "200":
        raise Exception("Error while twitter request " + resp["status"])

    user_json = json.loads(content.decode("UTF-8"))
    print(user_json)

    try:
        user = User.objects.get(id=user_json["id"])
        new_auth_token = uuid4()
        user.remember_me_token = new_auth_token
        user.lang = user_json["lang"]
        user.profile_icon = user_json["profile_image_url"]
        user.oauth_token = new_tokens["oauth_token"],
        user.oauth_secret = new_tokens["oauth_token_secret"]
        user.save()
    except User.DoesNotExist:
        new_user = User(
            id=user_json["id"],
            user_name=user_json["name"],
            lang=user_json["lang"],
            profile_icon=user_json["profile_image_url"],
            oauth_token=new_tokens["oauth_token"],
            oauth_secret=new_tokens["oauth_token_secret"]
        )
        new_user.save()
        new_auth_token = new_user.remember_me_token

    response = HttpResponseRedirect("/")

    response.set_cookie(settings.AUTH_COOKIE_KEY, new_auth_token, max_age=3 * 24 * 60 * 60)
    response.set_cookie("lang", user_json["lang"], max_age=30 * 24 * 60 * 60)

    return response


@allowed_methods(methods=["GET"])
@auth_is_required(True)
def home_page(request, user):

    model = {
        "current_user": user
    }

    return render(request, "twitter_vote/twitter_vote.html", model)


@allowed_methods(methods=["GET"])
@auth_is_required(False)
def load_votes(request, user):
    try:
        tweet_id = request.GET["tweet_id"]
    except KeyError:
        return HttpResponse("tweet_id param is not presented", status=400)

    try:
        tweet = Tweet.objects.get(id=tweet_id)
    except Tweet.DoesNotExist:
        return HttpResponse("tweet not found", status=404)

    try:
        user_tweet_vote = TweetVote.objects.get(tweet=tweet, user=user)
        tweet_vote_status = user_tweet_vote.vote_result
    except TweetVote.DoesNotExist:
        tweet_vote_status = "non"

    json_result = {
        "likesCount": tweet.likes_count,
        "dislikesCount": tweet.dislikes_count,
        "userVote": tweet_vote_status
    }
    return JsonResponse(json_result)


@allowed_methods(methods=["POST"])
@auth_is_required(False)
@transaction.atomic
def tweet_vote(request, user):
    json_data = json.loads(request.body)
    try:
        if json_data["voteStatus"] not in ["like", "dislike"]:
            return HttpResponse("voteStatus value is not valid", status=400)

        tweet = Tweet.objects.get(id=json_data["tweetId"])
        tweet_vote = TweetVote.objects.get(user=user, tweet=tweet)
        if tweet_vote is not None:
            if tweet_vote.vote_result == json_data["voteStatus"]:
                return JsonResponse({
                    "likesCount": tweet.likes_count,
                    "dislikesCount": tweet.dislikes_count,
                    "userVote": tweet_vote.vote_result
                })
            elif tweet_vote.vote_result == "like":
                tweet.likes_count -= 1
            elif tweet_vote.vote_result == "dislike":
                tweet.dislikes_count -= 1
            tweet_vote.delete()
    except KeyError as error:
        return HttpResponse(error, status=400)
    except Tweet.DoesNotExist:
        tweet = Tweet(id=json_data["tweetId"], likes_count=0, dislikes_count=0)
    except TweetVote.DoesNotExist:
        pass

    new_tweet_vote = TweetVote(user=user, tweet=tweet, vote_result=json_data["voteStatus"])
    if json_data["voteStatus"] == 'like':
        tweet.likes_count += 1
    elif json_data["voteStatus"] == "dislike":
        tweet.dislikes_count += 1

    tweet.save()
    new_tweet_vote.save()

    return JsonResponse({
        "likesCount": tweet.likes_count,
        "dislikesCount": tweet.dislikes_count,
        "userVote": new_tweet_vote.vote_result
    })


@allowed_methods(methods=["POST"])
@auth_is_required(False)
@transaction.atomic
def delete_vote(request, user):
    json_data = json.loads(request.body)
    try:
        tweet = Tweet.objects.get(id=json_data["tweetId"])
        tweet_vote = TweetVote.objects.get(user=user, tweet=tweet)
    except KeyError:
        return HttpResponse("tweetId value is required", status=400)
    except Tweet.DoesNotExist:
        return HttpResponse("tweet with given id is not exist", status=404)
    except TweetVote.DoesNotExist:
        return HttpResponse("you have not voted for that tweet", status=400)

    if tweet_vote.vote_result == "like":
        tweet.likes_count -= 1
    elif tweet_vote.vote_result == "dislike":
        tweet.dislikes_count -= 1

    tweet_vote.delete()
    tweet.save()

    return JsonResponse({
        "likesCount": tweet.likes_count,
        "dislikesCount": tweet.dislikes_count,
        "userVote": "non"
    })
