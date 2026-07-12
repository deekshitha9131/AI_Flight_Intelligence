# Database Entities

## Overview

The database is designed to support authentication, flight search, AI prediction, recommendations, analytics, and system administration.

---

# Core Entities

## 1. Users

Stores registered user accounts.

Purpose

- Authentication
- Authorization
- User profile
- Preferences ownership

---

## 2. UserPreferences

Stores personalized travel preferences.

Purpose

- Preferred airlines
- Preferred cabin
- Budget
- Currency
- Seat preference

---

## 3. Airports

Stores airport reference information.

Purpose

- Airport autocomplete
- Route lookup
- Location metadata

---

## 4. Airlines

Stores airline reference information.

Purpose

- Airline filtering
- Airline metadata
- Recommendation features

---

## 5. Searches

Stores every flight search performed.

Purpose

- Search history
- Analytics
- Recommendation input

---

## 6. FlightResults

Stores the flight options returned by a search (snapshot).

Purpose

- Preserve search results
- Prediction input
- Recommendation source

---

## 7. Predictions

Stores AI prediction outputs.

Purpose

- Predicted price
- Confidence score
- Buy/Wait recommendation

---

## 8. Recommendations

Stores personalized recommendations.

Purpose

- Ranked flights
- Recommendation score
- Explanation

---

## 9. Favorites

Stores saved flights.

Purpose

- User bookmarks
- Dashboard

---

## 10. Feedback

Stores user feedback.

Purpose

- Recommendation improvement
- User satisfaction

---

## 11. RefreshTokens

Stores refresh tokens.

Purpose

- Secure authentication
- Session management

---

## 12. AnalyticsEvents

Stores user interaction events.

Purpose

- Product analytics
- Usage reports
- Dashboard metrics