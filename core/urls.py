# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from django.urls import path, include  # add this
from django.conf.urls.i18n import i18n_patterns

urlpatterns = i18n_patterns(path("admin/", admin.site.urls))
urlpatterns += [
    path("i18n/", include("django.conf.urls.i18n")),
    # path('admin/', admin.site.urls),          # Django admin route
    path("api/", include("api.urls")),  # API url
    path("", include("apps.authentication.urls")),  # Auth routes - login / register

    # ADD NEW Routes HERE
    # Leave `Home.Urls` as last the last line
    path("", include("apps.home.urls")),
]