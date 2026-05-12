from django.contrib.auth.signals import user_login_failed, user_logged_in
from django.dispatch import receiver
from .models import User

@receiver(user_login_failed)
def track_failed_login(sender, credentials, **kwargs):
    username = credentials.get('username')
    try:
        user = User.objects.get(username=username)
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.is_active = False
        user.save()
    except User.DoesNotExist:
        # Username doesn't exist, nothing to lock
        pass

@receiver(user_logged_in)
def reset_failed_login(sender, user, **kwargs):
    user.failed_login_attempts = 0
    user.save()
