from django import forms
from django.contrib.auth import authenticate, get_user_model, login
from django.core.exceptions import ValidationError

User = get_user_model()


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput, label='نام کاربری یا شماره تلفن')
    password = forms.CharField( widget=forms.PasswordInput, label='رمز عبور')
    remember_me = forms.BooleanField(label='من را به خاطر بسپار', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # for field in self.fields.values():
        #     field.widget.attrs.update({
        #         'class': 'form-control',
        #         'placeholder': field.label,
        #     })

        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': self.fields['username'].label
        })

        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': self.fields['password'].label
        })
        self.fields['remember_me'].widget.attrs['class'] = 'form-check-input input-primary'


        for field in self.fields:
            if self.errors.get(field):
                self.fields[field].widget.attrs['class'] += ' is-invalid'

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        check_active = User.objects.filter(username=username, is_active=False).exists()
        if username and password:
            user = authenticate(username=username, password=password)
            if check_active:
                raise forms.ValidationError("حساب کاربری فعال نشده است!")
            elif user is None:
                raise forms.ValidationError("نام کاربری یا رمز عبور اشتباه است.")
            self.user = user
        return cleaned_data


class RegisterForm(forms.Form):
    phone_number = forms.CharField(label="شماره تلفن")
    first_name = forms.CharField(label="نام")
    last_name = forms.CharField(label="نام خانوادگی")
    email = forms.EmailField(label="ایمیل")
    password = forms.CharField(label="رمز عبور", widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="تکرار رمز عبور", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label,
            })

        for field in self.fields:
            if self.errors.get(field):
                self.fields[field].widget.attrs['class'] += ' is-invalid'



    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if User.objects.filter(phone_number=phone_number, username=phone_number).exists():
            raise ValidationError("این شماره قبلاً ثبت شده است.")
        return phone_number

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        if password and confirm and password != confirm:
            raise ValidationError("رمز عبور و تکرار آن یکسان نیستند.")
        return cleaned_data

    def save(self, request):
        user = User.objects.create_user(
            phone_number=self.cleaned_data['phone_number'],
            username=self.cleaned_data['phone_number'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'],

        )
        user.set_password(self.cleaned_data['password'])
        user.is_active = False
        user.save()
        return user

class CodeVerifyForm(forms.Form):
    code = forms.CharField(label="کد تأیید", max_length=6)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': self.fields['code'].label
        })

