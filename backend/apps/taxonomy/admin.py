from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .models import Family, Genus, Species, FunctionalGroup, Trait, TraitValue


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at", "uuid")
    list_per_page = 100


@admin.register(Genus)
class GenusAdmin(admin.ModelAdmin):
    list_display = ("name", "family")
    list_filter = ("family",)
    search_fields = ("name", "family__name")
    readonly_fields = ("species_list", "id", "created_at", "updated_at", "uuid")
    list_per_page = 100

    @admin.display(description="Species in Genus")
    def species_list(self, obj):
        species = obj.species.all()
        if not species:
            return "-"
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            ((s.get_admin_url(), s.scientific_name) for s in species),
        )


class TraitValueInline(admin.TabularInline):
    model = TraitValue
    extra = 0
    fields = ("trait", "min_value", "max_value")


@admin.register(FunctionalGroup)
class FunctionalGroupAdmin(admin.ModelAdmin):
    list_display = ("group_str", "species_count", "trait_count", "created_at")
    search_fields = ("group_id",)
    readonly_fields = ("id", "created_at", "updated_at", "species_list", "uuid")
    inlines = [TraitValueInline]

    @admin.display(description="Group")
    def group_str(self, obj):
        return str(obj)

    @admin.display(description="Number of Traits")
    def trait_count(self, obj):
        return obj.traits.count()

    @admin.display(description="Number of Species")
    def species_count(self, obj):
        return obj.species.count()

    @admin.display(description="Species in Group")
    def species_list(self, obj):
        species = obj.species.all()
        if not species:
            return "-"
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            ((s.get_admin_url(), s.scientific_name) for s in species),
        )


@admin.register(Trait)
class TraitAdmin(admin.ModelAdmin):
    list_display = ("type",)
    search_fields = ("type",)
    readonly_fields = ("id", "created_at", "updated_at", "uuid")


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = (
        "scientific_name",
        "life_form_display",
        "origin_display",
        "iucn_status_display",
    )
    list_filter = ("life_form", "origin", "iucn_status", "genus__family")
    search_fields = ("name", "genus__name", "accepted_scientific_name")
    raw_id_fields = ("genus", "functional_group")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "scientific_name",
        "gbif_url_link",
        "tropical_plants_url_link",
    )
    fieldsets = (
        (
            "Taxonomy",
            {
                "fields": (
                    "genus",
                    "name",
                    "accepted_scientific_name",
                    "scientific_name",
                )
            },
        ),
        (
            "Classification",
            {"fields": ("origin", "iucn_status", "life_form", "functional_group")},
        ),
        ("Physical Characteristics", {"fields": ("canopy_shape", "flower_color")}),
        (
            "External References",
            {"fields": ("gbif_id", "gbif_url_link", "tropical_plants_url_link")},
        ),
        ("Identification", {"fields": ("identified_by", "date")}),
        ("Metadata", {"fields": ("id", "created_at", "updated_at")}),
    )

    @admin.display(description="Life Form")
    def life_form_display(self, obj):
        return obj.get_life_form_display()

    @admin.display(description="Origin")
    def origin_display(self, obj):
        return obj.get_origin_display()

    @admin.display(description="IUCN Status")
    def iucn_status_display(self, obj):
        return obj.get_iucn_status_display()

    @admin.display(description="GBIF URL")
    def gbif_url_link(self, obj):
        if obj.gbif_url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">GBIF Link</a>',
                obj.gbif_url,
            )
        return "-"

    @admin.display(description="Tropical Plants URL")
    def tropical_plants_url_link(self, obj):
        if obj.tropical_plants_url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">Tropical Plants Link</a>',
                obj.tropical_plants_url,
            )
        return "-"
