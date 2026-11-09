from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    display_name = models.CharField(
        max_length=150,
        blank=True
    )

    bio = models.TextField(
        max_length=500,
        blank=True
    )

    profile_image_url = models.URLField(
        blank=True
    )

    timezone = models.CharField(
        max_length=50,
        default='UTC'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return self.user.username