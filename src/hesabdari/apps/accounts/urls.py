from django.urls import path

from hesabdari.apps.accounts.views import LoginView, RegisterView, VerifyView

namespace = 'accounts'

urlpatterns =[
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/', VerifyView.as_view(), name='verify'),
]