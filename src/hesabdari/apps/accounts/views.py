from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import View, FormView

from django.contrib.auth import get_user_model, login, logout
from urllib3 import request

from hesabdari.apps.accounts.forms import LoginForm, RegisterForm, CodeVerifyForm, ResetPasswordForm, PhoneForm
from hesabdari.apps.accounts.models import ActivationCode
from hesabdari.apps.accounts.utils.utils import send_sms_code

User = get_user_model()

# Create your views here.
class LoginView(FormView):
    form_class = LoginForm
    template_name = 'accounts/login-v1.html'
    success_url = reverse_lazy('home')

    # def dispatch(self, request, *args, **kwargs):
    #     print(request.user)
    #     if request.user.is_authenticated:
    #         return redirect('home')
    #     return super(LoginView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        # اولویت با پارامتر next است
        return self.request.POST.get('next') or self.request.GET.get('next') or self.success_url

    def form_valid(self, form):
        login(self.request, form.user)
        remember = form.cleaned_data.get('remember_me')
        if remember:
            self.request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
        else:
            # expires when closing browser
            self.request.session.set_expiry(0)
        return HttpResponseRedirect(self.get_success_url())


class RegisterView(FormView):
    template_name = 'accounts/register-v1.html'
    form_class = RegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save(self.request)
        activation, created = ActivationCode.objects.get_or_create(user=user)
        activation.generate_code()
        send_sms_code(user.phone_number, activation.code)
        self.request.session['uid'] = user.id
        return redirect('profile:verify')

class ForgetPasswordView(FormView):
    template_name = 'accounts/forget_password.html'
    form_class = PhoneForm
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super(ForgetPasswordView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = User.objects.filter(phone_number=form.cleaned_data['phone_number']).first()
        if not user:
            form.add_error('phone_number', 'این شماره تلفن در سامانه ثبت نشده است.')
            return self.form_invalid(form)
        activation, created = ActivationCode.objects.get_or_create(user=user)
        activation.generate_code()
        send_sms_code(user.phone_number, activation.code)
        self.request.session['uid'] = user.id
        return redirect('profile:reset_verify_password')

class ResetVerifyView(FormView):
    form_class = CodeVerifyForm
    template_name = 'accounts/reset_verify.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super(ResetVerifyView, self).dispatch(request, *args, **kwargs)

    def get_user(self):
        uid = self.request.session.get('uid')
        return User.objects.get(pk=uid)

    def form_valid(self, form):
        user = self.get_user()
        code = form.cleaned_data['code']
        activation, created = ActivationCode.objects.get_or_create(user=user)
        if not activation or activation.code != code:
            form.add_error('code', 'کد نادرست است.')
            return self.form_invalid(form)
        return redirect('profile:reset_password')

class ResetPasswordView(FormView):
    form_class = ResetPasswordForm
    template_name = 'accounts/reset-password.html'

    def get_user(self):
        uid = self.request.session.get('uid')
        return User.objects.filter(pk=uid).first()

    def form_valid(self, form):
        user = self.get_user()
        if not user:
            return redirect('forgot_password')

        user.set_password(form.cleaned_data['password'])
        user.save()

        ActivationCode.objects.filter(user=user).delete()
        del self.request.session['uid']

        return redirect('profile:login')


class VerifyView(FormView):
    template_name = 'accounts/verify.html'
    form_class = CodeVerifyForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super(VerifyView, self).dispatch(request, *args, **kwargs)

    def get_user(self):
        uid = self.request.session.get('uid')
        return User.objects.filter(pk=uid).first()

    def form_valid(self, form):
        user = self.get_user()
        if not user:
            return redirect('profile:register')

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
    request.session.flush()
    logout(request)
    return redirect('home')