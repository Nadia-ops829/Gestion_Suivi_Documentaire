from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        AGENT = 'AGENT', 'Transit'
        CHEF_SERVICE = 'CHEF_SERVICE', 'Validation'
        ADMIN = 'ADMIN', 'RSI'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.AGENT
    )
    failed_login_attempts = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
