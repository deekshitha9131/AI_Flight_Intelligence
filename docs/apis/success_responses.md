# Standard Success Response

Every successful API response follows a consistent format.

Example

{
  "success": true,
  "message": "Request completed successfully.",
  "data": {},
  "timestamp": "2026-07-11T10:15:00Z"
}

---

## Pagination Standard

For list endpoints:

{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_records": 248,
    "total_pages": 13,
    "has_next": true,
    "has_previous": false
  }
}

Default Values

- page = 1
- page_size = 20
- max_page_size = 100

---

## Authentication Rules

### Public Endpoints

- Register
- Login
- Forgot Password
- Reset Password
- Verify Email

### Authenticated Endpoints

Require a valid JWT access token.

### Admin Endpoints

Require:

- Valid JWT
- Admin role

### Token Expiration

- Access Token: 60 minutes
- Refresh Token: 7 days

### Authorization Header

Authorization: Bearer <access_token>