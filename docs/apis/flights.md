# Flight APIs

Base Path

/api/v1/flights

---

## Search Flights

GET /search

Parameters

origin

destination

departure_date

return_date

passengers

cabin

currency

Response

List of flights.

---

## Flight Details

GET /{flight_id}

Returns full flight information.

---

## Airport Autocomplete

GET /airports

Query

keyword

Returns airport suggestions.

---

## Airlines

GET /airlines

Returns supported airlines.