from django.contrib import admin
from .models import Measurement, Observation

# Measurement and Observation models from reports app are registered here.
admin.site.register(Measurement)
admin.site.register(Observation)