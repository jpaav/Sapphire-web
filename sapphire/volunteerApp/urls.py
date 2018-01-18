from django.conf.urls import url

from . import views
from utility.models import Event, Slot
from django.views.generic import ListView, DetailView


urlpatterns = [
    url(r'^feed/', views.feed, name='feed'),
    url(r'^calendar/', views.calendar, name='calendar'),
    url(r'^eventNeeds/', views.eventNeeds, name='eventNeeds'),
    url(r'^(?P<pk>\d+)$', DetailView.as_view(context_object_name="event", model = Event, template_name = "volunteer/event.html"), name='eventView'), #We should make this start with eventView instead of just having numbers
    url(r'^slotNeeds/', views.slotNeeds, name='slotNeeds'),
    url(r'^$', views.index, name='index'),      #NOTE This must be last otherwise it will always take precedent
]
