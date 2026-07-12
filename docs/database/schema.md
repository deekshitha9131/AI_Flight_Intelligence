# Database Schema

## Users

- id (UUID, PK)
- full_name
- email (Unique)
- password_hash
- role
- profile_picture
- email_verified
- created_at
- updated_at
- deleted_at

---

## UserPreferences

- id (UUID)
- user_id (FK)
- preferred_airline
- preferred_cabin
- budget
- preferred_currency
- created_at
- updated_at

---

## Airports

- airport_code (PK)
- airport_name
- city
- country
- latitude
- longitude

---

## Airlines

- airline_code (PK)
- airline_name
- country

---

## Searches

- id
- user_id
- origin
- destination
- departure_date
- return_date
- passengers
- cabin
- created_at

---

## FlightResults

- id
- search_id
- airline_code
- flight_number
- origin
- destination
- departure_time
- arrival_time
- duration_minutes
- stops
- price
- currency
- booking_url

---

## Predictions

- id
- search_id
- predicted_price
- confidence_score
- recommendation
- model_version
- created_at

---

## Recommendations

- id
- user_id
- flight_result_id
- score
- explanation
- created_at

---

## Favorites

- id
- user_id
- flight_result_id
- created_at

---

## Feedback

- id
- user_id
- recommendation_id
- rating
- comment
- created_at

---

## RefreshTokens

- id
- user_id
- token_hash
- expires_at
- revoked
- created_at

---

## AnalyticsEvents

- id
- user_id
- event_type
- metadata (JSONB)
- created_at