# Translation and Text Style Guide

This document outlines the text and translation style standards for the Urban Tree Observatory project, covering capitalization, punctuation, formatting, and general language guidelines for both English and Spanish.

## Table of Contents

1. [Capitalization Conventions](#capitalization-conventions)
2. [Punctuation Guidelines](#punctuation-guidelines)
3. [Formatting Standards](#formatting-standards)
4. [Technical Terminology](#technical-terminology)
5. [Language-Specific Considerations](#language-specific-considerations)
6. [Examples and Common Cases](#examples-and-common-cases)

## Capitalization Conventions

We follow different capitalization rules depending on the context and purpose of the text:

### Field Labels, Choice Options, and UI Elements

**Use lowercase** for field labels, model attributes, choice options, and other short UI elements:

```python
# Django model fields
name = models.CharField(_("species name"), max_length=100)
date_recorded = models.DateField(_("recording date"), null=True)

# Choice options
class IUCNStatus(models.TextChoices):
    DATA_DEFICIENT = "DD", _("data deficient")
    LEAST_CONCERN = "LC", _("least concern")
    NEAR_THREATENED = "NT", _("near threatened")
    VULNERABLE = "VU", _("vulnerable")
    ENDANGERED = "EN", _("endangered")
    CRITICALLY_ENDANGERED = "CR", _("critically endangered")
    EXTINCT_IN_WILD = "EW", _("extinct in the wild")
    EXTINCT = "EX", _("extinct")
    NOT_EVALUATED = "NE", _("not evaluated")

# Meta information
class Meta:
    verbose_name = _("species")
    verbose_name_plural = _("species")
```

**Spanish translation example:**

- "species name" → "nombre de la especie"
- "native" → "nativa"
- "species" → "especie"

### Sentences, Error Messages, and Notifications

**Use sentence case** (capitalize first letter only) for complete sentences, error messages, alerts, and notifications:

```python
# Error messages
raise ValidationError(_("This field is required"))

# Success messages
messages.success(request, _("Species was successfully updated"))

# Instructions
help_text=_("Enter the scientific name including genus and species")
```

**Spanish translation example:**

- "This field is required" → "Este campo es obligatorio"
- "Species was successfully updated" → "La especie fue actualizada correctamente"

### Titles and Headings

**Use sentence case** for page titles, section headings, and dialog titles:

```python
# Page title
page_title = _("Create new species record")

# Section header
section_header = _("Taxonomy information")
```

**Spanish translation example:**

- "Create new species record" → "Crear nuevo registro de especie"
- "Taxonomy information" → "Información taxonómica"

## Punctuation Guidelines

### Ending Punctuation

- **Omit trailing periods** for field labels, column headers, and short phrases
- **Include trailing periods** for complete sentences, including error messages and help text

```python
# Without period (field label)
species_name = models.CharField(_("scientific name"), max_length=100)

# With period (complete sentence in help text)
help_text=_("Enter the full scientific name with genus and species.")
```

### Colons in Labels

- **Omit colons** in field labels and form inputs - the UI framework will add these as needed
- If a label needs further explanation, use a separate help text field rather than adding it to the label

```python
# Correct
name_label = _("scientific name")
name_help = _("Enter in format: Genus species")

# Incorrect
name_label = _("scientific name: enter in format Genus species")
```

### Quotation Marks

- Use double quotes (`"`) for quoted content in English
- Use angular quotes (`«` and `»`) for quoted content in Spanish

## Formatting Standards

### Dates and Times

- Follow locale-specific formatting through Django's localization system
- Spell out month names in long formats
- Use 24-hour format for time representation

**English examples:**

- Short date: "Apr 15, 2025"
- Long date: "April 15, 2025"
- Time: "14:30"

**Spanish examples:**

- Short date: "15 abr 2025"
- Long date: "15 de abril de 2025"
- Time: "14:30"

### Numbers and Measurements

- Use the metric system for all measurements
- Follow locale-specific conventions for decimal and thousands separators
- Include a space between number and unit

**English examples:**

- Decimal: "3.5 m"
- Large number: "1,500 trees"

**Spanish examples:**

- Decimal: "3,5 m"
- Large number: "1.500 árboles"

## Technical Terminology

### Scientific Names

- Always capitalize genus, lowercase species: "Quercus ilex"
- Do not translate scientific names
- Italicize in UI display (handled via CSS, not in translation strings)

### Domain-Specific Terms

Maintain a consistent glossary for domain-specific terms across languages:

| English | Spanish | Notes |
|---------|---------|-------|
| carbon sequestration | secuestro de carbono | |
| diameter at breast height | diámetro a la altura del pecho | Abbreviated as DAP in Spanish |
| native | nativa | Plant origin |
| exotic | exótica | Plant origin |
| canopy | dosel | Tree structure |
| trunk | tronco | Tree structure |

## Language-Specific Considerations

### English

- Be concise and direct
- Use active voice when possible
- Avoid jargon and complex terminology outside of scientific contexts

### Spanish

- Spanish uses more words than English for the same concept - allow for text expansion
- Gender agreement is important - be consistent with masculine/feminine forms
- Use formal "usted" form for instructions and messages
- Avoid Anglicisms when Spanish terms exist

## Examples and Common Cases

### Form Field Labels

| Context | English | Spanish |
|---------|---------|---------|
| Field label | scientific name | nombre científico |
| Field label | recording date | fecha de registro |
| Field label | trunk height (m) | altura del tronco (m) |

### Choice Fields

| Context | English | Spanish |
|---------|---------|---------|
| Origin choice | native | nativa |
| Status choice | endangered | en peligro |
| Condition choice | good | bueno |

### Messages

| Context | English | Spanish |
|---------|---------|---------|
| Success | Changes saved successfully. | Cambios guardados correctamente. |
| Error | This field is required. | Este campo es obligatorio. |
| Confirmation | Are you sure you want to delete this record? | ¿Está seguro de que desea eliminar este registro? |

### Page Titles

| Context | English | Spanish |
|---------|---------|---------|
| List page | Species list | Lista de especies |
| Detail page | Species details | Detalles de la especie |
| Form page | Edit species | Editar especie |

## Practical Implementation

### In Django Templates

```html
{% trans "species list" %}  <!-- field label - lowercase -->
{% trans "Species record was created successfully." %}  <!-- sentence - sentence case -->
```

### In Python Code

```python
# Field label - lowercase
name = models.CharField(_("common name"), max_length=100)

# Error message - sentence case
raise ValidationError(_("Please enter a valid value."))
```

### In Angular Templates

```html
<!-- Field label - lowercase -->
<label>{{ 'species.fields.commonName' | translate }}</label>

<!-- Button - lowercase -->
<button>{{ 'common.buttons.save' | translate }}</button>

<!-- Message - sentence case -->
<p class="error">{{ 'validation.required' | translate }}</p>
```

---

By following these guidelines consistently, we ensure that both the English and Spanish versions of the application maintain a professional appearance and natural language flow while simplifying the translation process.
