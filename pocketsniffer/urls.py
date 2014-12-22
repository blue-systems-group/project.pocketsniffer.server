from django.conf.urls import patterns, url, include


urlpatterns = patterns('',
    url(r'^controller/', include('apps.controller.urls')),
    url(r'^backend/', include('apps.backend.urls')),
)
