from django.shortcuts import render, redirect
from django.views.generic import View, FormView

from django.contrib.auth import get_user_model, login, logout

from hesabdari.apps.accounts.forms import LoginForm, RegisterForm, CodeVerifyForm
from hesabdari.apps.accounts.models import ActivationCode
from hesabdari.apps.accounts.utils.utils import send_sms_code

User = get_user_model()

# Create your views here.
class LoginView(FormView):
    form_class = LoginForm
    template_name = 'accounts/login-v1.html'

    def form_valid(self, form):
        login(self.request, form.user)
        remember = form.cleaned_data.get('remember_me')
        if remember:
            self.request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
        else:
            # expires when closing browser
            self.request.session.set_expiry(0)
        return redirect('home')


class RegisterView(FormView):
    template_name = 'accounts/register-v1.html'
    form_class = RegisterForm

    def form_valid(self, form):
        user = form.save(self.request)
        activation, created = ActivationCode.objects.get_or_create(user=user)
        activation.generate_code()
        send_sms_code(user.phone_number, activation.code)
        self.request.session['uid'] = user.id
        return redirect('verify')

class VerifyView(FormView):
    template_name = 'accounts/verify.html'
    form_class = CodeVerifyForm

    def get_user(self):
        uid = self.request.session.get('uid')
        print(uid)
        return User.objects.filter(pk=uid).first()

    def form_valid(self, form):
        user = self.get_user()
        if not user:
            return redirect('register')

        code = form.cleaned_data['code']
        try:
            activation = ActivationCode.objects.get(user=user)
        except ActivationCode.DoesNotExist:
            form.add_error(None, "کد فعال‌سازی پیدا نشد")
            return self.form_invalid(form)

        if activation.is_expired():
            form.add_error(None, "کد منقضی شده است. لطفاً دوباره درخواست دهید.")
            return self.form_invalid(form)

        if activation.attempts >= 5:
            form.add_error(None, "تعداد تلاش بیش از حد مجاز است.")
            return self.form_invalid(form)

        if code == activation.code:
            user.is_active = True
            user.save()
            activation.delete()
            login(self.request, user)
            return redirect('home')
        else:
            activation.increment_attempt()
            form.add_error('code', 'کد اشتباه است.')
            return self.form_invalid(form)

def logout_view(request):
    logout(request)
    redirect('home')