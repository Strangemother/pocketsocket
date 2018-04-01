from django.forms import ModelForm
from channels import models


class ChannelForm(ModelForm):

    class Meta:
        model = models.Channel
        exclude = ['owner', 'created']
