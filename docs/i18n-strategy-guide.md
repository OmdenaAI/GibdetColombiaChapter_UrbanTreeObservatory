# Internationalization (i18n) Strategy Guide

This document outlines the comprehensive internationalization strategy for the Urban Tree Observatory project, which uses Django, Django REST Framework (DRF), and Angular.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Backend (Django/DRF) Implementation](#backend-djangodrf-implementation)
3. [Frontend (Angular) Implementation](#frontend-angular-implementation)
4. [API Communication Strategy](#api-communication-strategy)
5. [Database and Data Import Strategy](#database-and-data-import-strategy)
6. [Workflow for Adding/Updating Translations](#workflow-for-addingupdating-translations)
7. [Testing i18n Implementation](#testing-i18n-implementation)
8. [Best Practices and Common Pitfalls](#best-practices-and-common-pitfalls)

## Core Principles

- **Code in English**: All code, variable names, comments, and constants are in English
- **Short, language-neutral codes in database**: Use codes like `NA`, `CU` instead of words
- **Default user interface in Spanish**: Primary audience is Spanish-speaking
- **Support for English UI**: Secondary language support for international users
- **Separation of code from displayable text**: All user-facing text should be translatable

## Backend (Django/DRF) Implementation

### Django Settings Configuration

```python
# settings.py
LANGUAGE_CODE = "es"  # Default language
TIME_ZONE = "America/Bogota"  # Colombia timezone
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ("es", _("Spanish")),
    ("en", _("English")),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

MIDDLEWARE = [
    # ... other middleware
    "django.middleware.locale.LocaleMiddleware",  # Required for language detection
    # ... rest of middleware
]
```

### TextChoices Implementation

Correct approach for TextChoices:

```python
# WRONG - Mixed Spanish/English and no translations
class Origin(models.TextChoices):
    NATIVA = "Nativa", "Native"
    CULTIVADA = "Cultivada", "Cultivated"
    # ...

# CORRECT - English constants, neutral codes, translatable strings
from django.utils.translation import gettext_lazy as _

class Origin(models.TextChoices):
    NATIVE = "NA", _("native")
    CULTIVATED = "CU", _("cultivated") 
    NOT_IDENTIFIED = "NI", _("not identified")
    NATIVE_CULTIVATED = "NC", _("native | cultivated")
    NATURALIZED = "NU", _("naturalized")
    ENDEMIC = "EN", _("endemic")
    NATURALIZED_CULTIVATED = "NL", _("naturalized | cultivated")
```

### Text Capitalization and Style

We follow specific capitalization conventions for different types of text in our application. See our [Translation and Text Style Guide](./translation-style-guide.md) for detailed guidelines on:

- Capitalization for different text types (field labels, error messages, etc.)
- Punctuation in translatable strings
- Formatting conventions for dates, numbers, and units
- Handling technical terminology

Consistency in these areas significantly improves the user experience and simplifies the translation process.

### Using Translation Functions

Two main translation functions:

1. **gettext_lazy**: For model definitions, admin configurations

   ```python
   from django.utils.translation import gettext_lazy as _
   
   class MyModel(models.Model):
       name = models.CharField(_("name"), max_length=100)
   ```

2. **gettext**: For immediate translation in views, form methods

   ```python
   from django.utils.translation import gettext as _
   
   def clean_email(self):
       if error:
           raise ValidationError(_("Invalid email address"))
   ```

### Django Admin Configuration

```python
from django.utils.translation import gettext_lazy as _

class SpeciesAdmin(admin.ModelAdmin):
    fieldsets = [
        (_("Taxonomy"), {
            "fields": ["family", "genus", "name", "scientific_name"]
        }),
        (_("Classification"), {
            "fields": ["origin", "iucn_status", "growth_habit"]
        }),
    ]
    list_display = ["scientific_name", "get_origin_display"]
    list_filter = ["origin", "iucn_status"]
    search_fields = ["name", "scientific_name"]
```

### DRF Serializers

```python
from django.utils.translation import gettext_lazy as _

class SpeciesSerializer(serializers.ModelSerializer):
    # Add display text for choice fields
    origin_display = serializers.CharField(source="get_origin_display", read_only=True)
    
    class Meta:
        model = Species
        fields = ["id", "name", "scientific_name", "origin", "origin_display"]
        
    def validate_name(self, value):
        if not value:
            raise serializers.ValidationError(_("Species name cannot be empty"))
        return value
```

### Custom Fields for Localized Responses

```python
class LocalizedChoiceField(serializers.ChoiceField):
    """Choice field that returns localized display values"""
    def to_representation(self, value):
        if value in ("", None):
            return value
        # Get the translated display text
        return str(self._choices.get(value, value))
```

## Frontend (Angular) Implementation

### Setup ngx-translate

1. Install the packages:

   ```bash
   npm install @ngx-translate/core @ngx-translate/http-loader
   ```

2. Configure in app module:

   ```typescript
   // app.module.ts
   import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
   import { TranslateHttpLoader } from '@ngx-translate/http-loader';
   import { HttpClient } from '@angular/common/http';
   
   export function HttpLoaderFactory(http: HttpClient) {
     return new TranslateHttpLoader(http, './assets/i18n/', '.json');
   }
   
   @NgModule({
     imports: [
       // Other imports
       TranslateModule.forRoot({
         loader: {
           provide: TranslateLoader,
           useFactory: HttpLoaderFactory,
           deps: [HttpClient]
         },
         defaultLanguage: 'es'
       })
     ]
   })
   export class AppModule { }
   ```

3. Initialize in app component:

   ```typescript
   // app.component.ts
   import { TranslateService } from '@ngx-translate/core';
   
   @Component({/* ... */})
   export class AppComponent {
     constructor(private translate: TranslateService) {
       // Default and fallback language
       translate.setDefaultLang('es');
       
       // Get saved language or use browser language
       const savedLang = localStorage.getItem('language') || 
                         translate.getBrowserLang() || 
                         'es';
       translate.use(savedLang);
     }
   }
   ```

### Translation Files Structure

Create translation files in `/assets/i18n/`:

```json
// es.json
{
  "common": {
    "buttons": {
      "save": "Guardar",
      "cancel": "Cancelar",
      "edit": "Editar",
      "delete": "Eliminar"
    }
  },
  "species": {
    "fields": {
      "scientificName": "Nombre científico",
      "commonName": "Nombre común"
    },
    "origin": {
      "native": "Nativa",
      "exotic": "Exótica",
      "unknown": "Desconocido"
    }
  }
}
```

```json
// en.json
{
  "common": {
    "buttons": {
      "save": "Save",
      "cancel": "Cancel",
      "edit": "Edit",
      "delete": "Delete"
    }
  },
  "species": {
    "fields": {
      "scientificName": "Scientific name",
      "commonName": "Common name"
    },
    "origin": {
      "native": "Native",
      "exotic": "Exotic",
      "unknown": "Unknown"
    }
  }
}
```

### Using Translations in Angular

1. In templates:

   ```html
   <!-- Simple strings -->
   <button>{{ 'common.buttons.save' | translate }}</button>
   
   <!-- With parameters -->
   <p>{{ 'species.count' | translate:{ count: totalSpecies } }}</p>
   
   <!-- HTML content -->
   <div [innerHTML]="'species.description' | translate"></div>
   ```

2. In TypeScript:

   ```typescript
   import { TranslateService } from '@ngx-translate/core';
   
   constructor(private translateService: TranslateService) {}
   
   showMessage() {
     const message = this.translateService.instant('messages.success');
     // Use message in alerts, etc.
   }
   
   switchLanguage(lang: string) {
     this.translateService.use(lang);
     localStorage.setItem('language', lang);
   }
   ```

## API Communication Strategy

### Language Detection and Switching

1. Setting language in Angular HTTP requests:

   ```typescript
   // api.service.ts
   import { HttpClient, HttpHeaders } from '@angular/common/http';
   import { TranslateService } from '@ngx-translate/core';
   
   @Injectable()
   export class ApiService {
     constructor(
       private http: HttpClient,
       private translateService: TranslateService
     ) {}
     
     getHeaders(): HttpHeaders {
       return new HttpHeaders({
         'Accept-Language': this.translateService.currentLang
       });
     }
     
     getSpecies() {
       return this.http.get('/api/species/', { headers: this.getHeaders() });
     }
   }
   ```

2. Processing language header in Django:

   ```python
   # The LocaleMiddleware will handle this automatically
   # Just ensure it's properly configured in settings.py
   ```

### API Response Localization

Strategy 1: Return both code and display value:

```json
{
  "id": 1,
  "name": "Quercus ilex",
  "origin": {
    "code": "NA",
    "display": "Nativa" 
  }
}
```

Strategy 2: Expand serializer with display values:

```python
class SpeciesSerializer(serializers.ModelSerializer):
    origin_display = serializers.CharField(source="get_origin_display", read_only=True)
    
    class Meta:
        model = Species
        fields = ["id", "name", "origin", "origin_display"]
```

## Database and Data Import Strategy

### Handling CSV Imports with Spanish Data

Use mapping dictionaries to convert Spanish terms to database codes:

```python
# mappings.py
from apps.taxonomy.models import Species

ORIGIN_MAPPINGS = {
    "Nativa": Species.Origin.NATIVE,
    "Exótica": Species.Origin.EXOTIC,
    "Exotica": Species.Origin.EXOTIC,
    "Desconocido": Species.Origin.UNKNOWN
}

def get_mapped_value(value, mapping_dict, default=None):
    """Get mapped value from dictionary with case-insensitive lookup"""
    if not value:
        return default
        
    # Try direct lookup
    if value in mapping_dict:
        return mapping_dict[value]
    
    # Try case-insensitive lookup
    value_lower = value.lower()
    for k, v in mapping_dict.items():
        if k.lower() == value_lower:
            return v
    
    return default
```

Using the mappings during import:

```python
def process_taxonomy_data(data):
    for row in data:
        origin = get_mapped_value(
            row.get("origin", ""),
            ORIGIN_MAPPINGS,
            Species.Origin.UNKNOWN
        )
        
        species = Species.objects.create(
            name=row.get("name", ""),
            origin=origin,
            # Other fields...
        )
```

### Database Content Guidelines

1. **Enumerated values**: Store as neutral codes (e.g., "NA" not "Nativa")
2. **Free text user input**: Store as-is (in Spanish if user entered in Spanish)
3. **Scientific names**: Store as-is (universal nomenclature)
4. **Generated responses**: Don't store translated text, generate at runtime

## Workflow for Adding/Updating Translations

### Django Translations

1. Mark strings for translation in code:

   ```python
   from django.utils.translation import gettext_lazy as _
   
   title = _("Species List")
   ```

2. Extract messages:

   ```bash
   python manage.py makemessages -l es
   python manage.py makemessages -l en
   ```

3. Edit translation files in `locale/[lang]/LC_MESSAGES/django.po`

4. Compile messages:

   ```bash
   python manage.py compilemessages
   ```

### Angular Translations

1. Add new keys to translation files in `/assets/i18n/`

2. Use translations in components

3. Consider using translation management tools for larger projects:
   - BabelEdit
   - Lokalise
   - POEditor

## Testing i18n Implementation

### Backend Testing

```python
from django.test import TestCase
from django.utils import translation
from apps.taxonomy.models import Species
from apps.taxonomy.serializers import SpeciesSerializer

class I18nTestCase(TestCase):
    def setUp(self):
        self.species = Species.objects.create(
            name="Oak",
            origin=Species.Origin.NATIVE
        )
    
    def test_origin_display_localization(self):
        # Test Spanish translation
        with translation.override("es"):
            serializer = SpeciesSerializer(self.species)
            self.assertEqual(serializer.data["origin_display"], "Nativa")
        
        # Test English translation
        with translation.override("en"):
            serializer = SpeciesSerializer(self.species)
            self.assertEqual(serializer.data["origin_display"], "Native")
```

### Frontend Testing

```typescript
import { TestBed } from '@angular/core/testing';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

describe('TranslationService', () => {
  let translateService: TranslateService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        TranslateModule.forRoot()
      ]
    });
    
    translateService = TestBed.inject(TranslateService);
    translateService.setTranslation('es', {
      'species.origin.native': 'Nativa'
    });
    translateService.setTranslation('en', {
      'species.origin.native': 'Native'
    });
    translateService.setDefaultLang('es');
  });

  it('should translate according to current language', () => {
    translateService.use('es');
    expect(translateService.instant('species.origin.native')).toBe('Nativa');
    
    translateService.use('en');
    expect(translateService.instant('species.origin.native')).toBe('Native');
  });
});
```

## Best Practices and Common Pitfalls

### Best Practices

1. **Avoid string concatenation** for translated text:

   ```python
   # BAD
   message = _("Hello") + ", " + user.name
   
   # GOOD - With placeholders
   message = _("Hello, %(name)s") % {"name": user.name}
   ```

2. **Use context for ambiguous terms**:

   ```python
   from django.utils.translation import pgettext_lazy
   
   # "Trunk" can mean different things
   tree_trunk = pgettext_lazy("tree part", "trunk")
   elephant_trunk = pgettext_lazy("elephant body part", "trunk")
   ```

3. **Keep translations organized** with namespaces:

   ```python
   species.fields.name
   species.actions.create
   common.buttons.save
   ```

4. **Document specialized terminology** in a glossary for translators

### Common Pitfalls

1. **Hardcoded strings** in templates or code
2. **Using non-lazy translation** in model definitions
3. **Forgetting to compile messages** after updates
4. **Not handling pluralization** correctly
5. **Assuming translated text length** will be similar to original
6. **Not escaping variables** in translated strings

### Performance Considerations

1. **Lazy loading** of translation files in Angular
2. **Caching API responses** with language-specific keys
3. **Server-side rendering** with correct initial language

---

This strategy provides a comprehensive approach to internationalization for the Urban Tree Observatory project. By following these guidelines, the application will provide a consistent experience for both Spanish and English users while maintaining clean, maintainable code.
