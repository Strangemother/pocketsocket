from django.urls import path
from client import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='client'),
]
