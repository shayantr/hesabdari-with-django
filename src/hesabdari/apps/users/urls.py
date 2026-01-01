from django.urls import path

from hesabdari.apps.users.views import LoginView, RegisterView, VerifyView, logout_view, ResetPasswordView, \
    ForgetPasswordView, ResetVerifyView

app_name = 'profile'

urlpatterns =[
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/', VerifyView.as_view(), name='verify'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('forget-password/', ForgetPasswordView.as_view(), name='forget_password'),
    path('reset_verify/', ResetVerifyView.as_view(), name='reset_verify_password'),
    path('logout/', logout_view, name='logout'),
]