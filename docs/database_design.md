# Database Design

## Overview

The AI Flight Intelligence Platform uses PostgreSQL as its primary relational database.

The database is designed to support:

- User authentication
- Flight search history
- AI predictions
- Personalized recommendations
- Analytics
- Feedback collection

---

# Entity Relationship Overview

Users
│
├── Searches
│      │
│      ├── Predictions
│      │
│      └── Recommendations
│
├── Favorites
│
├── Feedback
│
Flights
│
Airports
│
Analytics

---

# Tables

## 1. Users

Stores registered users.

| Column | Type |
|---------|------|
| id | UUID (PK) |
| full_name | VARCHAR(100) |
| email | VARCHAR(255) UNIQUE |
| password_hash | TEXT |
| profile_picture | TEXT |
| preferred_currency | VARCHAR(10) |
| preferred_cabin | VARCHAR(30) |
| favorite_airline | VARCHAR(100) |
| is_verified | BOOLEAN |
| role | ENUM(User, Admin) |
| created_at | TIMESTAMP |
| updated_at | TIMESTAMP |

---

## 2. Airports

| Column | Type |
|---------|------|
| airport_code | VARCHAR(10) PK |
| airport_name | VARCHAR(200) |
| city | VARCHAR(100) |
| country | VARCHAR(100) |
| latitude | DECIMAL |
| longitude | DECIMAL |

---

## 3. Flights

Stores searched flight information.

| Column | Type |
|---------|------|
| id | UUID |
| flight_number | VARCHAR |
| airline |
| origin |
| destination |
| departure_time |
| arrival_time |
| duration |
| cabin |
| stops |
| price |
| currency |
| booking_url |
| created_at |

---

## 4. Searches

Stores every search performed.

| Column | Type |
|---------|------|
| id | UUID |
| user_id | FK |
| origin |
| destination |
| departure_date |
| return_date |
| passengers |
| cabin |
| search_time |

---

## 5. Predictions

Stores ML predictions.

| Column | Type |
|---------|------|
| id | UUID |
| search_id | FK |
| predicted_price |
| confidence_score |
| recommendation |
| model_version |
| prediction_time |

---

## 6. Recommendations

Stores recommended flights.

| Column | Type |
|---------|------|
| id | UUID |
| user_id | FK |
| flight_id | FK |
| recommendation_score |
| explanation |
| created_at |

---

## 7. Favorites

| Column | Type |
|---------|------|
| id | UUID |
| user_id | FK |
| flight_id | FK |
| saved_at |

---

## 8. Analytics

Stores aggregated analytics.

| Column | Type |
|---------|------|
| id | UUID |
| metric_name |
| metric_value |
| recorded_at |

---

## 9. Feedback

| Column | Type |
|---------|------|
| id | UUID |
| user_id | FK |
| rating |
| comment |
| submitted_at |

---

# Relationships

User
 ├── Searches
 ├── Favorites
 ├── Feedback
 └── Recommendations

Search
 └── Prediction

Recommendation
 └── Flight

Flight
 ├── Airport (Origin)
 └── Airport (Destination)

---

# Indexes

- email
- airport_code
- origin
- destination
- departure_date
- prediction_time
- search_time
- recommendation_score

---

# Constraints

- Email must be unique
- Airport code must exist
- Price > 0
- Confidence Score between 0 and 100
- Rating between 1 and 5