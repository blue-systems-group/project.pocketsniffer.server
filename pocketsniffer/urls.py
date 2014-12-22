from django.conf.urls import patterns, url, include


urlpatterns = patterns('',
    url(r'^backend/', include('apps.backend.urls')),
    url(r'^controller/', include('apps.controller.urls')),
)
