
from __future__ import unicode_literals

from django.shortcuts import render
from django.views.generic import TemplateView, ListView, CreateView, DeleteView
from django.contrib.auth import  get_user_model

from django.http.response import HttpResponseRedirect
from channels import models, forms


class WebSocketSessionMixin(object):

    def add_wss_to_dict(self, mdict):
        if 'ws_session' not in mdict:
            mdict['ws_session'] = self.get_wss()
        return mdict

    def get_wss(self):
        return self.request.environ.get('WEBSOCKET_SESSION', None)

    def get_context_data(self, **kwargs):
        res = super().get_context_data(**kwargs)
        self.add_wss_to_dict(res)
        return res


class IndexView(WebSocketSessionMixin, TemplateView):
    template_name = "channels/index.html"


class ChannelDeleteView(WebSocketSessionMixin, DeleteView):
    success_url = '/channels/list/'
    model = models.Channel


from django.http import JsonResponse

class ChannelListView(WebSocketSessionMixin, ListView):
    model = models.Channel

    def get(self, request, *args, **kwargs):

        if kwargs.get('as_json', False) is True:
            # return json response
            return JsonResponse(self.get_data(request), safe=False)
        return super(ChannelListView, self).get(self, request, *args, **kwargs)

    def get_data(self, request):
        data = self.get_queryset()
        res =  tuple(data.values('name', 'public', 'created', 'owner'))
        return res

    def get_queryset(self):
        queryset = super(ChannelListView, self).get_queryset()
        if self.request.user.is_anonymous:
            queryset = queryset.filter(public=True)
        else:
            queryset = queryset.filter(owner=self.request.user)
        return queryset


class ChannelCreateView(WebSocketSessionMixin, CreateView):
    model = models.Channel
    form_class = forms.ChannelForm
    success_url = '/channels/list/'


    def form_valid(self, form):
        form.instance.owner = self.request.user
        wss = self.get_wss()
        if wss is not None:
            data = form.cleaned_data
            print('Adding new channel to service')

            print( wss.channels.create_channel(data['name'], {}))

        return super().form_valid(form)
