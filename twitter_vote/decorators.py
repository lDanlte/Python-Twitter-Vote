from functools import wraps

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.conf import settings

from twitter_vote.models import User


def allowed_methods(methods):
    def decorator(function):

        @wraps(function)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return HttpResponse("method %s is not allowed" % request.method, status=405)
            return function(request, *args, **kwargs)

        return wrapper

    return decorator


def auth_is_required(redirect_if_auth_failed=False):
    def decorator(func):

        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                auth_token = request.COOKIES[settings.AUTH_COOKIE_KEY]
                user = User.objects.get(remember_me_token=auth_token)
            except (KeyError, User.DoesNotExist):
                user = None

            if user is None:
                if redirect_if_auth_failed:
                    return HttpResponseRedirect("/authorize")
                else:
                    return HttpResponse("not authorized", status=401)
            kwargs["user"] = user
            return func(request, *args, **kwargs)

        return wrapper

    return decorator
