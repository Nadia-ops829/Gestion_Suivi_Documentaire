from django.db import models

class AppSettings(models.Model):
    """
    Paramètres globaux de l'application (Configuration RSI)
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = "Paramètre"
        verbose_name_plural = "Paramètres"
