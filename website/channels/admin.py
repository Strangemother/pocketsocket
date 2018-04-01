from django.contrib import admin
from channels import models

# Register your models here.
@admin.register(models.Channel)
class ChannelAdmin(admin.ModelAdmin):
    pass
