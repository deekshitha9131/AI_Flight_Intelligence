# Database Naming Conventions

## Table Names

Use plural snake_case.

Examples

users

flight_results

analytics_events

---

## Column Names

Use snake_case.

Examples

created_at

departure_time

confidence_score

preferred_currency

---

## Primary Keys

Always use

id

(UUID)

---

## Foreign Keys

Use

<entity>_id

Examples

user_id

search_id

recommendation_id

---

## Boolean Fields

Use prefixes

is_

has_

Examples

is_verified

has_notifications

---

## Timestamp Fields

Every transactional table includes

created_at

updated_at

deleted_at (Soft Delete)

---

## Enum Fields

Use PostgreSQL ENUMs where appropriate.

Examples

role

cabin

recommendation

---

## UUID

Use UUIDs for all application-generated IDs except stable reference tables like Airports and Airlines, which can use their natural codes (IATA).