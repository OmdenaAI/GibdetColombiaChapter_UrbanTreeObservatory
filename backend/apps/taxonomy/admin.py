from django.contrib import admin
from .models import Family, Genus, Species

# Family, Genus, and Species models from taxonomy app are registered here.
admin.site.register(Family)
admin.site.register(Genus)
admin.site.register(Species)