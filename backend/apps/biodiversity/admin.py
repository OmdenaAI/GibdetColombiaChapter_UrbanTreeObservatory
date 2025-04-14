from django.contrib import admin
from .models import Place, BiodiversityRecord

# Place and BiodiversityRecord models from biodiversity app are registered here.
admin.site.register(Place)
admin.site.register(BiodiversityRecord)