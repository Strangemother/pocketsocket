"""website URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.conf.urls import include
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
import re
from website.views import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('client/', include('client.urls')),
    path('static/', serve, kwargs={"document_root":settings.STATIC_ROOT, "show_indexes": True}),
    path('static/<path:path>', serve, kwargs={"document_root":settings.STATIC_ROOT, "show_indexes": True}),
]# + static('static/', document_root=settings.STATIC_ROOT)
