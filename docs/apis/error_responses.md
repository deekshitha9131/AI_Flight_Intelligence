# Standard Error Response

All API errors follow a common structure.

Example

{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Departure date must be in the future.",
    "details": [
      {
        "field": "departure_date",
        "issue": "Invalid date"
      }
    ]
  },
  "timestamp": "2026-07-11T10:15:00Z",
  "path": "/api/v1/flights/search"
}

Common Error Codes

VALIDATION_ERROR

UNAUTHORIZED

FORBIDDEN

NOT_FOUND

CONFLICT

RATE_LIMIT_EXCEEDED

EXTERNAL_API_ERROR

MODEL_UNAVAILABLE

DATABASE_ERROR

INTERNAL_SERVER_ERROR