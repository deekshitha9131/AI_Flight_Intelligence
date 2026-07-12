# Database Indexes

## Primary Keys

- users.id
- searches.id
- flight_results.id
- predictions.id
- recommendations.id
- favorites.id

---

## Unique Indexes

- users.email
- airports.airport_code
- airlines.airline_code

---

## Search Indexes

searches(origin)

searches(destination)

searches(departure_date)

flight_results(price)

flight_results(airline_code)

flight_results(departure_time)

recommendations(score)

analytics_events(event_type)

---

## Composite Indexes

(origin, destination)

(origin, destination, departure_date)

(user_id, created_at)

(search_id, airline_code)

---

## Full Text Search

Airport Name

Airport City

Airline Name

---

## JSON Index

GIN Index

analytics_events.metadata