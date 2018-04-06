from django.urls import path
from channels import views

urlpatterns = [
    path('', views.IndexView.as_view()),
    path('list/', views.ChannelListView.as_view(), name='channel-list'),
    path('list/json', views.ChannelListView.as_view(), { "as_json": True}, name='channel-list', ),
    path('create/', views.ChannelCreateView.as_view(), name='channel-create'),
    path('delete/<int:pk>', views.ChannelDeleteView.as_view(), name='channel-delete'),
]
