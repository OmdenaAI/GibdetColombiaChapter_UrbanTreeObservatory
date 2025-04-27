# Urban Tree Observatory API Documentation

## API Overview

The Urban Tree Observatory API provides access to data about urban trees in Ibagué, Colombia, including taxonomic information, geographical data, tree measurements, and observations. The API is built using Django REST Framework and follows RESTful principles.

## Authentication

The API uses JWT (JSON Web Token) authentication. To obtain a token:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

The response will contain an access token and a refresh token:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1..."
}
```

To use the access token, include it in the Authorization header:

```http
GET /api/v1/taxonomy/species/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1...
```

Some endpoints are read-only and may not require authentication.

## API Endpoints

The API is organized around the following main resources:

### Taxonomy

- `GET /api/v1/taxonomy/families/` - List all plant families
- `GET /api/v1/taxonomy/families/{id}/` - Retrieve a specific family
- `GET /api/v1/taxonomy/genera/` - List all genera
- `GET /api/v1/taxonomy/genera/{id}/` - Retrieve a specific genus
- `GET /api/v1/taxonomy/species/` - List all species
- `GET /api/v1/taxonomy/species/{id}/` - Retrieve a specific species
- `GET /api/v1/taxonomy/functional-groups/` - List all functional groups
- `GET /api/v1/taxonomy/functional-groups/{id}/` - Retrieve a specific functional group
- `GET /api/v1/taxonomy/traits/` - List all traits
- `GET /api/v1/taxonomy/traits/{id}/` - Retrieve a specific trait

### Places

- `GET /api/v1/places/countries/` - List all countries
- `GET /api/v1/places/countries/{id}/` - Retrieve a specific country
- `GET /api/v1/places/departments/` - List all departments
- `GET /api/v1/places/departments/{id}/` - Retrieve a specific department
- `GET /api/v1/places/municipalities/` - List all municipalities
- `GET /api/v1/places/municipalities/{id}/` - Retrieve a specific municipality
- `GET /api/v1/places/localities/` - List all localities
- `GET /api/v1/places/localities/{id}/` - Retrieve a specific locality
- `GET /api/v1/places/neighborhoods/` - List all neighborhoods
- `GET /api/v1/places/neighborhoods/{id}/` - Retrieve a specific neighborhood
- `GET /api/v1/places/sites/` - List all sites
- `GET /api/v1/places/sites/{id}/` - Retrieve a specific site

### Biodiversity Records

- `GET /api/v1/biodiversity/records/` - List all biodiversity records
- `GET /api/v1/biodiversity/records/{id}/` - Retrieve a specific biodiversity record
- `GET /api/v1/biodiversity/records/near/` - List records near a specific point
- `GET /api/v1/biodiversity/records/bbox/` - List records within a bounding box
- `GET /api/v1/biodiversity/records/by_neighborhood/` - List records in a specific neighborhood
- `GET /api/v1/biodiversity/records/by_locality/` - List records in a specific locality
- `POST /api/v1/biodiversity/records/by_polygon/` - List records within a custom polygon

### Reports

- `GET /api/v1/reports/measurements/` - List all measurements
- `GET /api/v1/reports/measurements/{id}/` - Retrieve a specific measurement
- `GET /api/v1/reports/observations/` - List all observations
- `GET /api/v1/reports/observations/{id}/` - Retrieve a specific observation

### Climate

- `GET /api/v1/climate/stations/` - List all weather stations
- `GET /api/v1/climate/stations/{id}/` - Retrieve a specific weather station
- `GET /api/v1/climate/stations/near/` - List stations near a specific point
- `GET /api/v1/climate/data/` - List climate data
- `GET /api/v1/climate/data/{id}/` - Retrieve a specific climate data record

## Query Parameters

Most list endpoints support the following query parameters:

- `search`: Search across relevant text fields
- `ordering`: Order results by specific fields (prefix with `-` for descending order)
- `page`: Page number for pagination
- `page_size`: Number of results per page (default: 20, max: 100)
- `format`: Response format (e.g., `json`, `geojson` for geographic data)

### Example Queries

#### Filter species by family

```http
GET /api/v1/taxonomy/species/?genus__family=1
```

#### Search for trees by common name

```http
GET /api/v1/biodiversity/records/?search=acacia
```

#### Find trees near a location

```http
GET /api/v1/biodiversity/records/near/?lat=4.4378&lon=-75.2012&radius=500
```

#### Get trees in a specific neighborhood

```http
GET /api/v1/biodiversity/records/by_neighborhood/?id=1&format=geojson
```

#### Filter trees by neighborhood and species

```http
GET /api/v1/biodiversity/records/?neighborhood=1&species=5
```

#### Filter trees by locality and date range

```http
GET /api/v1/biodiversity/records/?neighborhood__locality=2&date_from=2023-01-01&date_to=2023-12-31
```

#### Filter measurements by type and value range

```http
GET /api/v1/reports/measurements/?attribute=HT&value_min=10&value_max=20
```

#### Find weather stations near a location

```http
GET /api/v1/climate/stations/near/?lat=4.4378&lon=-75.2012&radius=5000
```

#### Get climate data for a specific station within a date range

```http
GET /api/v1/climate/data/?station=1&date_from=2023-01-01&date_to=2023-01-31
```

#### Filter climate data by temperature range

```http
GET /api/v1/climate/data/?sensor=t2m&value_min=20&value_max=30
```

#### Find trees within a custom polygon

```http
POST /api/v1/biodiversity/records/by_polygon/
Content-Type: application/json

{
  "polygon": [
    [-75.2157, 4.4401],
    [-75.2078, 4.4405],
    [-75.2082, 4.4353],
    [-75.2149, 4.4348],
    [-75.2157, 4.4401]
  ],
  "limit": 500
}
```

## GeoJSON Support

The following endpoints support GeoJSON format by adding `?format=geojson` parameter:

### Places GeoJSON

```http
GET /api/v1/places/countries/?format=geojson
GET /api/v1/places/departments/?format=geojson
GET /api/v1/places/municipalities/?format=geojson
GET /api/v1/places/localities/?format=geojson
GET /api/v1/places/neighborhoods/?format=geojson
```

### Biodiversity Records GeoJSON

```http
GET /api/v1/biodiversity/records/?format=geojson
GET /api/v1/biodiversity/records/near/?lat=4.4378&lon=-75.2012&radius=500&format=geojson
GET /api/v1/biodiversity/records/bbox/?min_lon=-75.25&min_lat=4.40&max_lon=-75.19&max_lat=4.45&format=geojson
GET /api/v1/biodiversity/records/by_neighborhood/?id=1&format=geojson
GET /api/v1/biodiversity/records/by_locality/?id=1&format=geojson
```

### Weather Stations GeoJSON

```http
GET /api/v1/climate/stations/?format=geojson
```

## Spatial Filtering

The API provides several methods for spatial filtering of biodiversity records:

### 1. Point-radius search

```http
GET /api/v1/biodiversity/records/near/?lat=4.4378&lon=-75.2012&radius=500
```

### 2. Bounding box search

```http
GET /api/v1/biodiversity/records/bbox/?min_lon=-75.25&min_lat=4.40&max_lon=-75.19&max_lat=4.45
```

### 3. Administrative boundary search

```http
GET /api/v1/biodiversity/records/by_neighborhood/?id=1
GET /api/v1/biodiversity/records/by_locality/?id=2
GET /api/v1/biodiversity/records/?neighborhood=3
GET /api/v1/biodiversity/records/?neighborhood__locality=2
```

### 4. Custom polygon search

```http
POST /api/v1/biodiversity/records/by_polygon/
Content-Type: application/json

{
  "polygon": [
    [longitude1, latitude1],
    [longitude2, latitude2],
    ...
    [longitudeN, latitudeN],
    [longitude1, latitude1]  /* The polygon must be closed */
  ]
}
```

> **Note**: This endpoint uses POST instead of GET because polygon coordinates can become quite lengthy and complex, potentially exceeding URL length limits. Using POST allows sending polygon data in the request body as JSON, providing better support for polygons with many vertices while maintaining a clean, readable data structure.

## Pagination

The API uses page-based pagination. The response includes:

```json
{
  "count": 100,
  "next": "http://example.com/api/v1/taxonomy/species/?page=2",
  "previous": null,
  "results": [
    // Data
  ]
}
```

You can adjust the page size with the `page_size` parameter (up to 100):

```http
GET /api/v1/taxonomy/species/?page=2&page_size=50
```

## Rate Limiting

The API has rate limiting to prevent abuse. Please check the response headers for rate limit information:

- `X-RateLimit-Limit`: Maximum number of requests allowed per period
- `X-RateLimit-Remaining`: Number of requests remaining in the current period
- `X-RateLimit-Reset`: Time until the rate limit resets

## Error Handling

The API uses standard HTTP status codes to indicate success or failure:

- 200 OK: Request succeeded
- 400 Bad Request: Invalid request
- 401 Unauthorized: Authentication required
- 403 Forbidden: Permission denied
- 404 Not Found: Resource not found
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server error

Error responses include a JSON body with details:

```json
{
  "detail": "Error message"
}
```

## Performance Considerations

Some endpoints contain large datasets:

- **Climate Data**: Over 700,000 records - always use filters (date ranges, station, sensor type) when querying this endpoint
- **Biodiversity Records**: Contains extensive tree census data
- **Measurements and Observations**: Contains detailed measurement records

To optimize performance:

1. Always use filtering parameters when available
2. Limit result sets using pagination
3. Use date ranges for time-series data
4. Request only the data you need
5. For map-based applications:
   - Use GeoJSON format where available
   - Prefer the dedicated spatial endpoints (near, bbox, by_neighborhood, by_locality, by_polygon)
   - Set appropriate limits on the number of records returned
   - Consider using clustering on the frontend for large datasets
   - Request detailed information only when needed (e.g., after a user selects a specific feature)
