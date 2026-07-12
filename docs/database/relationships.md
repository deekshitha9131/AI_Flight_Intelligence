# Database Relationships

Users
│
├── UserPreferences (1:1)
│
├── Searches (1:N)
│
├── Favorites (1:N)
│
├── Feedback (1:N)
│
├── Recommendations (1:N)
│
└── RefreshTokens (1:N)

Searches
│
├── FlightResults (1:N)
│
└── Predictions (1:1)

FlightResults
│
├── Recommendations (1:N)
│
└── Favorites (1:N)

Recommendations
│
└── Feedback (1:N)

Airports
│
└── Referenced by FlightResults

Airlines
│
└── Referenced by FlightResults