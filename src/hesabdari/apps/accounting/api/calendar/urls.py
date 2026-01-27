from django.urls import path

from hesabdari.apps.accounting.api.calendar.views import cheques_of_day, all_events, calendar_page

urlpatterns = [
    path('events/', calendar_page, name='calendar_page'),
    path('events-list/', all_events, name='events_list'),
    path('cheque-day/', cheques_of_day, name='cheque_day'),
]