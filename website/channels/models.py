from django.db import models

from django.conf import settings
# Create your models here.
class Channel(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        )
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    public = models.BooleanField(default=False)
