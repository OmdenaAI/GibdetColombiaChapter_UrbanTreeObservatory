# Urban Tree Observatory Testing Strategy

## Overview

This document outlines the testing strategy for the Urban Tree Observatory project, including test types, coverage goals, and best practices for writing and maintaining tests.

## Testing Philosophy

Our testing approach is guided by the following principles:

1. **Test business-critical functionality first**: Prioritize testing key features that directly impact the core functionality and user experience.
2. **Balance coverage and maintainability**: Aim for comprehensive test coverage without creating brittle or difficult-to-maintain tests.
3. **Test behavior, not implementation**: Focus on testing the behavior of the application from a user perspective rather than the internal implementation details.
4. **Follow the testing pyramid**: Implement a balanced mix of unit, integration, and end-to-end tests, with more tests at the lower levels.

## Test Types

### Unit Tests

Unit tests verify individual components in isolation. In our context, this typically means testing:

- Model methods and properties
- Serializer behavior
- Helper functions and utilities

Examples:

- Testing string representations of models
- Testing model validation
- Testing custom serializer methods

### Integration Tests

Integration tests verify that different components work together correctly. These include:

- API endpoint tests
- Database interaction tests
- Service-to-service communication tests

Examples:

- Testing API endpoints return correct data
- Testing filtering and querying capabilities
- Testing relationships between models

### End-to-End Tests

End-to-end tests verify the application works correctly from a user perspective, testing the entire system as a whole.

Examples:

- Testing user flows through the frontend application
- Testing data visualization features
- Testing map interactions

## Testing Tools

The Urban Tree Observatory uses the following testing tools:

### Backend

- **pytest**: Primary testing framework
- **pytest-django**: Django-specific testing utilities
- **factory_boy**: Test data generation
- **coverage**: Test coverage reporting
- **django.test.Client**: Simple request testing
- **rest_framework.test.APIClient**: REST API testing

### Frontend

- **Jest**: JavaScript testing framework
- **Testing Library**: Component testing
- **Cypress**: End-to-end testing (future implementation)

## Test Directory Structure

Tests are organized to mirror the application structure:

```text
backend/
  ├── apps/
  │   ├── app_name/
  │   │   ├── tests/
  │   │   │   ├── __init__.py
  │   │   │   ├── test_models.py     # Unit tests for models
  │   │   │   ├── test_serializers.py  # Unit tests for serializers
  │   │   │   ├── test_api.py        # Integration tests for API endpoints
  │   │   │   └── test_views.py      # Tests for views (if not using DRF)
  │   │   │
frontend/
  ├── src/
  │   ├── components/
  │   │   ├── __tests__/
  │   │   │   ├── ComponentName.test.js
```

## Test Fixtures

We use centralized fixtures in `backend/conftest.py` to promote reuse and consistency. These fixtures provide:

- Test data generation using factory_boy
- Authentication setup
- Common test utilities

## Writing Effective Tests

### Best Practices for Backend Tests

1. **Use descriptive test names**: Test names should describe the behavior being tested, not just the function name.

   ```python
   # Good
   def test_biodiversity_record_filter_by_neighborhood():

   # Not as good
   def test_filter():
   ```

2. **One assertion per test**: Where possible, keep tests focused on one behavior.

3. **Use factories**: Use factory_boy to generate test data rather than creating objects manually.

   ```python
   # Good
   biodiversity_record = BiodiversityRecordFactory(species=species, site=site)

   # Avoid
   biodiversity_record = BiodiversityRecord.objects.create(species=species, site=site, ...)
   ```

4. **Use pytest marks**: Use pytest marks to categorize tests.

   ```python
   @pytest.mark.django_db
   @pytest.mark.slow
   def test_complex_query():
       # Test implementation
   ```

5. **Isolate tests**: Tests should be independent and not rely on the state from previous tests.

### Testing API Endpoints

When testing API endpoints, focus on:

1. **Status codes**: Verify the endpoint returns the correct status code
2. **Response structure**: Verify the response has the expected structure
3. **Filtering**: Test that filters work correctly
4. **Permissions**: Test that authorization rules are enforced
5. **Error handling**: Test error conditions and responses

Example:

```python
@pytest.mark.django_db
def test_biodiversity_record_list(api_client, biodiversity_record):
    url = reverse("biodiversity:biodiversity-record-list")
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["common_name"] == biodiversity_record.common_name
```

### Testing Geospatial Features

For geospatial features, test the following:

1. **Coordinate accuracy**: Verify that coordinates are correctly stored and retrieved
2. **Spatial queries**: Test spatial filters like proximity, bounding boxes, and polygons
3. **GeoJSON output**: Verify that GeoJSON responses have the correct structure
4. **Boundary calculations**: Test functions that calculate areas or perform spatial operations

Example:

```python
@pytest.mark.django_db
def test_near_endpoint(api_client, fixed_location_record):
    url = reverse("biodiversity:biodiversity-record-near") + "?lat=4.3&lon=-75.2&radius=100"
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == fixed_location_record.id
```

## Test Coverage Goals

We aim for the following test coverage goals:

- **Models and core business logic**: 90%+ coverage
- **API endpoints and serializers**: 80%+ coverage
- **View functions**: 70%+ coverage
- **Edge cases and error handling**: 70%+ coverage

Priority areas for testing:

1. Biodiversity record management and querying
2. Geospatial features and mapping capabilities
3. Data import/export functionality
4. User authentication and permissions

## Running Tests

### Backend Tests

Run all tests:

```bash
docker compose exec backend pytest
```

Run tests for a specific app:

```bash
docker compose exec backend pytest apps/biodiversity/tests/
```

Run tests with coverage:

```bash
docker compose exec backend pytest --cov=apps
```

Generate coverage report:

```bash
docker compose exec backend pytest --cov=apps --cov-report=html
```

### Frontend Tests

Run all tests:

```bash
docker compose exec frontend npm test
```

Run tests for a specific component:

```bash
docker compose exec frontend npm test -- ComponentName
```

## Continuous Integration

Tests are run automatically in our CI pipeline:

1. On every pull request to the main branch
2. On every push to the main branch
3. Nightly builds to catch regressions

Test failures in the CI pipeline block merging of pull requests to ensure code quality.

## Test-Driven Development

We encourage test-driven development (TDD) for complex features or bug fixes:

1. Write a failing test that demonstrates the required behavior or reproduces the bug
2. Implement the minimum code needed to make the test pass
3. Refactor the code while keeping the tests passing

## Mock and Stub Best Practices

For tests that involve external dependencies:

1. Use pytest monkeypatch for simple dependency mocking
2. Use unittest.mock for more complex mocking needs
3. Create dedicated test doubles for frequently used external dependencies
4. Clearly document the expected behavior of mocked components

## Future Improvements

Areas for future testing improvements:

1. Implement end-to-end testing with Cypress
2. Increase test coverage for frontend components
3. Add performance testing for critical endpoints
4. Implement visual regression testing for map and visualization components
5. Establish load testing for production deployment readiness
