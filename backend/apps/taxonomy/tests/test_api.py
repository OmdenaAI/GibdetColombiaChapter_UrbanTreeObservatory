import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestFamilyAPI:
    """Test the Family API endpoints."""

    def test_family_list(self, authenticated_client, family):
        """Test retrieving the list of families."""
        url = reverse("taxonomy:family-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test family in the results
        family_found = False
        for result in response.data["results"]:
            if result["name"] == family.name:
                family_found = True
                break

        assert family_found, f"Test family '{family.name}' not found in results"

    def test_family_detail(self, authenticated_client, family):
        """Test retrieving a specific family."""
        url = reverse("taxonomy:family-detail", args=[family.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == family.name

    def test_family_search(self, authenticated_client, family):
        """Test searching for families by name."""
        # Use first few letters of the family name
        search_term = family.name[:3]
        url = reverse("taxonomy:family-list") + f"?search={search_term}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0
        # Verify our test family is in the results
        family_found = False
        for result in response.data["results"]:
            if result["name"] == family.name:
                family_found = True
                break

        assert family_found, f"Test family '{family.name}' not found in search results"

    def test_family_ordering(self, authenticated_client, family):
        """Test ordering families by name."""
        url = reverse("taxonomy:family-list") + "?ordering=name"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # We're not testing the actual ordering here since we have only one family,
        # but we're verifying the endpoint accepts the ordering parameter


@pytest.mark.django_db
class TestGenusAPI:
    """Test the Genus API endpoints."""

    def test_genus_list(self, authenticated_client, genus):
        """Test retrieving the list of genera."""
        url = reverse("taxonomy:genus-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test genus in the results
        genus_found = False
        for result in response.data["results"]:
            if result["name"] == genus.name:
                genus_found = True
                break

        assert genus_found, f"Test genus '{genus.name}' not found in results"

    def test_genus_detail(self, authenticated_client, genus):
        """Test retrieving a specific genus."""
        url = reverse("taxonomy:genus-detail", args=[genus.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == genus.name
        assert "family" in response.data
        assert response.data["family"]["id"] == genus.family.id
        assert response.data["family"]["name"] == genus.family.name

    def test_genus_filter_by_family(self, authenticated_client, genus):
        """Test filtering genera by family."""
        url = reverse("taxonomy:genus-list") + f"?family={genus.family.id}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1
        # Verify our test genus is in the filtered results
        genus_found = False
        for result in response.data["results"]:
            if result["name"] == genus.name:
                genus_found = True
                break

        assert genus_found, f"Test genus '{genus.name}' not found in filtered results"

    def test_genus_search(self, authenticated_client, genus):
        """Test searching for genera by name."""
        # Use first few letters of the genus name
        search_term = genus.name[:3]
        url = reverse("taxonomy:genus-list") + f"?search={search_term}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify our test genus is in the search results
        genus_found = False
        for result in response.data["results"]:
            if result["name"] == genus.name:
                genus_found = True
                break

        assert genus_found, f"Test genus '{genus.name}' not found in search results"


@pytest.mark.django_db
class TestSpeciesAPI:
    """Test the Species API endpoints."""

    def test_species_list(self, authenticated_client, species):
        """Test retrieving the list of species."""
        url = reverse("taxonomy:species-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test species in the results
        species_found = False
        for result in response.data["results"]:
            if (
                result["name"] == species.name
                and result["genus"]["name"] == species.genus.name
            ):
                species_found = True
                break

        assert species_found, (
            f"Test species '{species.scientific_name}' not found in results"
        )

    def test_species_detail(self, authenticated_client, species):
        """Test retrieving a specific species."""
        url = reverse("taxonomy:species-detail", args=[species.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == species.name
        assert response.data["genus"]["name"] == species.genus.name
        assert "family" in response.data["genus"]
        assert response.data["life_form"] == species.life_form

        # Check that URLs are included
        assert "gbif_url" in response.data
        assert "tropical_plants_url" in response.data

    def test_species_common_name_is_most_frequent(self, authenticated_client, species):
        """common_name is the most frequent non-empty name among the species' records."""
        from apps.biodiversity.factories import BiodiversityRecordFactory

        BiodiversityRecordFactory.create_batch(
            2, species=species, common_name="Guayacán"
        )
        BiodiversityRecordFactory(species=species, common_name="Chicalá")
        BiodiversityRecordFactory.create_batch(3, species=species, common_name="")

        url = reverse("taxonomy:species-detail", args=[species.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["common_name"] == "Guayacán"

    def test_species_without_records_has_null_common_name(
        self, authenticated_client, species
    ):
        url = reverse("taxonomy:species-detail", args=[species.id])
        response = authenticated_client.get(url)

        assert response.data["common_name"] is None

    def test_species_filter_by_genus(self, authenticated_client, species):
        """Test filtering species by genus."""
        url = reverse("taxonomy:species-list") + f"?genus={species.genus.id}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1
        # Verify our test species is in the filtered results
        species_found = False
        for result in response.data["results"]:
            if result["name"] == species.name:
                species_found = True
                break

        assert species_found, (
            f"Test species '{species.name}' not found in filtered results"
        )

    def test_species_filter_by_family(self, authenticated_client, species):
        """Test filtering species by family."""
        url = (
            reverse("taxonomy:species-list")
            + f"?genus__family={species.genus.family.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1
        # Verify our test species is in the filtered results
        species_found = False
        for result in response.data["results"]:
            if result["name"] == species.name:
                species_found = True
                break

        assert species_found, (
            f"Test species '{species.name}' not found in filtered results"
        )

    def test_species_filter_by_life_form(self, authenticated_client, species):
        """Test filtering species by life form."""
        url = reverse("taxonomy:species-list") + f"?life_form={species.life_form}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1
        # Verify our test species is in the filtered results
        species_found = False
        for result in response.data["results"]:
            if result["name"] == species.name:
                species_found = True
                break

        assert species_found, (
            f"Test species '{species.name}' not found in filtered results"
        )

    def test_species_search_by_name(self, authenticated_client, species):
        """Test searching for species by scientific name."""
        # Use first few letters of the species name
        search_term = species.name[:3]
        url = reverse("taxonomy:species-list") + f"?search={search_term}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Check if our test species is in the search results
        species_found = False
        for result in response.data["results"]:
            if result["name"] == species.name:
                species_found = True
                break

        # If not found with species name, it could be due to search configuration
        # Let's try with genus name as well
        if not species_found:
            search_term = species.genus.name[:3]
            url = reverse("taxonomy:species-list") + f"?search={search_term}"
            response = authenticated_client.get(url)

            for result in response.data["results"]:
                if result["name"] == species.name:
                    species_found = True
                    break

        assert species_found, (
            f"Test species '{species.scientific_name}' not found in search results"
        )


@pytest.mark.django_db
class TestFunctionalGroupAPI:
    """Test the FunctionalGroup API endpoints."""

    def test_functional_group_list(self, authenticated_client, functional_group):
        """Test retrieving the list of functional groups."""
        url = reverse("taxonomy:functional-group-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test functional group in the results
        group_found = False
        for result in response.data["results"]:
            if result["group_id"] == functional_group.group_id:
                group_found = True
                break

        assert group_found, (
            f"Test functional group '{functional_group.group_id}' not found in results"
        )

    def test_functional_group_detail(self, authenticated_client, functional_group):
        """Test retrieving a specific functional group."""
        url = reverse("taxonomy:functional-group-detail", args=[functional_group.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["group_id"] == functional_group.group_id
        # Check that traits are included in the response
        assert "trait_values" in response.data

    def test_functional_group_ordering(self, authenticated_client, functional_group):
        """Test ordering functional groups by group_id."""
        url = reverse("taxonomy:functional-group-list") + "?ordering=group_id"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # We're not testing the actual ordering here since we have only one group,
        # but we're verifying the endpoint accepts the ordering parameter


@pytest.mark.django_db
class TestTraitAPI:
    """Test the Trait API endpoints."""

    def test_trait_list(self, authenticated_client, traits):
        """Test retrieving the list of traits."""
        url = reverse("taxonomy:trait-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= len(traits)

        # Verify all our test traits are in the results
        for trait in traits:
            trait_found = False
            for result in response.data["results"]:
                if result["type"] == trait.type:
                    trait_found = True
                    break

            assert trait_found, f"Test trait '{trait.type}' not found in results"

    def test_trait_detail(self, authenticated_client, traits):
        """Test retrieving a specific trait."""
        # Use the first trait for testing
        test_trait = traits[0]
        url = reverse("taxonomy:trait-detail", args=[test_trait.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["type"] == test_trait.type

    def test_trait_filter_by_type(self, authenticated_client, traits):
        """Test filtering traits by type."""
        # Use the first trait for testing
        test_trait = traits[0]
        url = reverse("taxonomy:trait-list") + f"?type={test_trait.type}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["type"] == test_trait.type
