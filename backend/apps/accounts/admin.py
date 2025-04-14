from django.contrib import admin
from .models import UserProfile

# UserProfile model from accounts app is registered here.
admin.site.register(UserProfile)