from django.urls import path

from hesabdari.apps.home import views

urlpatterns =[
    path('', views.home, name='home'),
    path('sidebar/', views.sidebar, name='sidebar'),
]