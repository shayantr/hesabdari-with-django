import random
import uuid
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# Create your models here.

class User(AbstractUser):
    phone_number = models.CharField(max_length=12, unique=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    password_reset_token = models.CharField(
        max_length=100,  # A UUID is 32 chars, plus hyphens for some formats
        unique=True,
        blank=True,
        null=True,
        help_text="توکن ریست پسورد."
    )
    password_reset_token_expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when the password reset token expires."
    )

    def generate_password_reset_token(self):
        """Generates a new unique token and sets an expiration time."""
        # Ensure old token is cleared before generating a new one to maintain uniqueness
        self.password_reset_token = str(uuid.uuid4())  # Generate a UUID for uniqueness
        # Set expiration, e.g., 1 hour from now
        self.password_reset_token_expires_at = timezone.now() + timezone.timedelta(hours=1)
        self.save()
        return self.password_reset_token

    def is_password_reset_token_valid(self, token):
        """Checks if the given token is valid and not expired."""
        if not self.password_reset_token:
            return False  # No token exists for this user

        if self.password_reset_token != token:
            return False  # Token mismatch

        if self.password_reset_token_expires_at and \
                self.password_reset_token_expires_at < timezone.now():
            self.clear_password_reset_token()  # Clear expired token
            return False  # Token has expired

        return True

    def clear_password_reset_token(self):
        """Clears the password reset token and its expiration time."""
        self.password_reset_token = None
        self.password_reset_token_expires_at = None
        self.save()


    class Meta:
        db_table = 'user'

class ActivationCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveIntegerField(default=0)

    def generate_code(self):
        self.code = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.attempts = 0
        self.save()

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    def increment_attempt(self):
        self.attempts += 1
        self.save()

    def __str__(self):
        return f"{self.user.username} - {self.code}"

    class Meta:
        db_table = 'activation_code'

