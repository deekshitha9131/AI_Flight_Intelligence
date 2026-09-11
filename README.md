# ✈️ AI Flight Intelligence

An AI-powered flight intelligence platform built with **Python, FastAPI, PostgreSQL, Machine Learning, LLMs, React, and TypeScript**.

The application allows users to search for flights, interact with an AI travel assistant using natural language, receive flight-price predictions and recommendations, save preferences, and maintain conversation history.

The project is intentionally designed as a **student-level portfolio project**: technically meaningful, easy to understand, and practical without unnecessary enterprise complexity.

---

## 🎯 Project Objective

The goal of AI Flight Intelligence is to demonstrate practical software engineering and AI development skills through one complete application.

The project demonstrates:

* Python backend development
* FastAPI REST API development
* PostgreSQL database design
* SQLAlchemy ORM
* JWT authentication
* External API integration
* Natural-language processing with an LLM
* Prompt engineering
* Structured LLM output
* Context-aware AI conversations
* Machine-learning-based flight price prediction
* Recommendation and ranking logic
* React + TypeScript frontend development
* Automated testing
* Docker-based local deployment

---

# 🚀 Core Features

## 1. User Authentication

Users can:

* Register
* Login
* Logout
* Access protected endpoints
* Maintain an authenticated session
* Update their profile

Authentication uses:

* JWT access tokens
* Password hashing
* Protected FastAPI routes

---

## 2. Flight Search

Users can search for flights using:

* Origin
* Destination
* Departure date
* Optional return date
* Number of passengers
* Cabin class
* Currency

The application integrates with an external flight provider when configured.

The system normalizes provider responses into a consistent internal flight representation.

### Important rule

The application must never fabricate real flight results.

If the external provider is unavailable, the application clearly reports that flight data could not be retrieved.

---

## 3. AI Flight Assistant

Users can communicate with the application using natural language.

Examples:

```text
Find flights from Hyderabad to Delhi tomorrow.
```

```text
I want to fly from Bangalore to Mumbai next Friday.
```

```text
What is the cheapest option?
```

```text
Can you find something in the morning?
```

The AI assistant extracts structured information such as:

* Intent
* Origin
* Destination
* Departure date
* Return date
* Cabin class
* Passenger count
* Time preference
* Price-related requests

The extracted information is validated by the backend before being used.

---

## 4. Context-Aware Conversations

The assistant maintains conversation context.

For example:

```text
User:
Find flights from Hyderabad to Delhi tomorrow.

Assistant:
Here are the available flights...

User:
Which one is cheapest?

Assistant:
The cheapest available option is...
```

The assistant can use relevant previous conversation information when processing follow-up requests.

Explicitly stated new routes replace the previous route context.

---

## 5. Flight Price Prediction

The application includes a lightweight machine-learning component that predicts an estimated flight price based on available flight/search features.

The purpose is educational and portfolio-oriented rather than production-grade airfare forecasting.

The ML component demonstrates:

* Feature preparation
* Model training
* Model serialization
* Model loading
* Prediction
* API integration

Predictions are clearly labeled as estimates.

---

## 6. Flight Recommendations

The system ranks available flights using factors such as:

* Price
* Duration
* Number of stops
* Departure time
* User preferences

The recommendation engine produces a simple explanation of why a flight was recommended.

Example:

```text
Recommended because it has the lowest price
while maintaining a reasonable travel duration.
```

---

## 7. User Preferences

Users can save preferences such as:

* Preferred cabin
* Preferred currency
* Preferred airport
* Preferred price range
* Preferred travel time

These preferences can influence recommendations.

---

## 8. Conversation History

Authenticated users can:

* Create conversations
* Continue conversations
* Retrieve previous messages
* View conversation history
* Delete conversations

Conversation data is stored in PostgreSQL.

---

# 🤖 AI Capabilities

The project intentionally demonstrates several AI-related concepts without introducing unnecessary AI frameworks.

### Natural Language Understanding

The LLM converts natural-language travel requests into structured information.

Example:

```text
"Find me a cheap morning flight from Hyderabad to Delhi
next Monday for two people."
```

becomes approximately:

```json
{
  "intent": "flight_search",
  "origin": "HYD",
  "destination": "DEL",
  "departure_date": "2026-09-07",
  "passengers": 2,
  "cabin": "ECONOMY",
  "time_preference": "morning",
  "price_preference": "cheap"
}
```

The backend validates this structured output before performing a search.

### Prompt Engineering

The application uses explicit prompts for:

* Intent detection
* Flight parameter extraction
* Assistant response generation
* Recommendation explanation

### Context Management

Relevant conversation history is supplied to the AI assistant to support follow-up questions.

### Machine Learning

A separate ML model handles flight-price prediction.

This demonstrates the distinction between:

```text
LLM → language understanding and conversation

ML model → numerical price prediction

Backend → business logic and validation
```

---

# 🏗️ Architecture

```text
                         ┌─────────────────────┐
                         │   React Frontend    │
                         │   TypeScript + Vite │
                         └──────────┬──────────┘
                                    │
                               HTTP / JSON
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │      API Layer      │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
             Auth Service     Flight Service    AI Service
                  │                 │                 │
                  │                 │          ┌──────▼──────┐
                  │                 │          │ LLM Provider│
                  │                 │          └─────────────┘
                  │                 │
                  │          ┌──────▼─────────┐
                  │          │ Flight Provider│
                  │          └────────────────┘
                  │
                  └──────────────┬─────────────────────┐
                                 │                     │
                                 ▼                     ▼
                          ┌─────────────┐       ┌─────────────┐
                          │ PostgreSQL  │       │ ML Model    │
                          │             │       │             │
                          │ Users       │       │ Prediction  │
                          │ Flights     │       │             │
                          │ Conversations│      └─────────────┘
                          │ Preferences │
                          └─────────────┘
```

---

# 🧩 Backend Structure

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── flights.py
│   │       ├── assistant.py
│   │       ├── predictions.py
│   │       ├── recommendations.py
│   │       ├── conversations.py
│   │       └── preferences.py
│   │
│   ├── ai/
│   │   ├── prompts/
│   │   ├── llm.py
│   │   └── assistant.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── dependencies.py
│   │
│   ├── database/
│   │   ├── session.py
│   │   └── base.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── flight.py
│   │   ├── prediction.py
│   │   └── preference.py
│   │
│   ├── repositories/
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── flight.py
│   │   └── preference.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── flight.py
│   │   ├── assistant.py
│   │   ├── prediction.py
│   │   └── preference.py
│   │
│   ├── services/
│   │   ├── auth.py
│   │   ├── flight.py
│   │   ├── assistant.py
│   │   ├── prediction.py
│   │   ├── recommendation.py
│   │   └── conversation.py
│   │
│   └── main.py
│
├── tests/
├── alembic/
├── requirements.txt
├── .env.example
└── Dockerfile
```

---

# 🎨 Frontend Structure

```text
frontend/
├── src/
│   ├── api/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   ├── store/
│   ├── types/
│   ├── utils/
│   ├── App.tsx
│   └── main.tsx
│
├── package.json
├── vite.config.ts
└── Dockerfile
```

The frontend remains intentionally simple.

---

# 🗄️ Database

PostgreSQL is the only application database.

Core tables:

```text
users
    │
    ├── conversations
    │       │
    │       └── messages
    │
    ├── preferences
    │
    ├── predictions
    │
    └── flight searches
```

### Main entities

| Entity        | Purpose                           |
| ------------- | --------------------------------- |
| User          | Authentication and profile        |
| Conversation  | Chat session                      |
| Message       | Individual user/assistant message |
| Flight Search | Search request/history            |
| Prediction    | Price prediction record           |
| Preference    | User travel preferences           |

No additional database is required.

---

# 🔄 Application Workflow

## Standard Flight Search

```text
User
 ↓
React UI
 ↓
FastAPI endpoint
 ↓
Flight Service
 ↓
External Flight Provider
 ↓
Normalize provider response
 ↓
Return FlightResponse
 ↓
React UI
```

---

## AI Flight Search

```text
User natural-language request
 ↓
FastAPI Assistant Endpoint
 ↓
Retrieve conversation context
 ↓
LLM
 ↓
Structured Flight Intent
 ↓
Backend validation
 ↓
Flight Service
 ↓
External Flight Provider
 ↓
Flight Results
 ↓
LLM Response Generation
 ↓
Save conversation
 ↓
Return response
```

---

## Price Prediction

```text
Flight/Search Features
 ↓
Feature Preparation
 ↓
Trained ML Model
 ↓
Prediction
 ↓
Store Prediction
 ↓
Return Estimated Price
```

---

## Recommendation

```text
Flight Results
 ↓
Preference Information
 ↓
Scoring Function
 ↓
Rank Flights
 ↓
Generate Recommendation Explanation
 ↓
Return Recommended Flights
```

---

# 🛡️ AI Behavioral Rules

The AI assistant must follow these rules:

1. Never fabricate real flight data.
2. Flight results must originate from the configured flight provider.
3. AI-generated price predictions must be clearly identified as estimates.
4. Missing required flight information must be requested.
5. The assistant must not invent dates.
6. A new explicit origin/destination pair replaces the previous route.
7. Follow-up questions should use relevant conversation context.
8. Provider failures must be communicated honestly.
9. Unsupported information must not be fabricated.
10. General travel advice must be distinguishable from real-time flight information.

---

# 🛠️ Technology Stack

## Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* PostgreSQL
* Alembic
* PyJWT / compatible JWT library
* Password hashing
* Pytest

## AI

* LLM API
* Prompt engineering
* Structured output
* Natural-language understanding
* Conversation context
* Machine learning
* Scikit-learn
* Joblib

## Frontend

* React
* TypeScript
* Vite
* React Router
* Simple state management
* CSS

## Infrastructure

* Docker
* Docker Compose

---

# 🔌 External Integrations

The project uses two main external AI/data integrations.

### Flight Provider

Used for real flight search results.

### LLM Provider

Used for:

* Intent extraction
* Flight parameter extraction
* Conversational responses
* Recommendation explanations

The exact provider implementation is isolated behind a small service interface so the rest of the application does not depend directly on provider-specific code.

---

# 📋 Frozen Scope

The following features are included:

* User registration
* User login
* JWT authentication
* Flight search
* External flight provider integration
* Natural-language flight requests
* AI assistant
* Conversation context
* Conversation persistence
* Price prediction
* Flight recommendations
* User preferences
* React frontend
* Automated tests
* Docker deployment

---

# 🚫 Explicitly Out of Scope

To keep the project small and finishable, the following are NOT part of the project:

* CrewAI
* LangGraph
* LangChain
* Multi-agent systems
* Microservices
* Redis
* Celery
* Kafka
* WebSockets
* Vector databases
* RAG pipelines
* Booking/payment processing
* Hotel booking
* Travel insurance
* Admin dashboard
* Mobile application
* Voice assistant
* Real-time notifications
* Complex ML training pipelines
* Multiple databases

These features would add complexity without significantly improving the portfolio value of this student project.

---

# 🧪 Testing Strategy

Testing focuses on the important behavior rather than achieving artificial 100% coverage.

### Unit Tests

Test:

* Authentication utilities
* Flight parameter validation
* AI output parsing
* Recommendation scoring
* Prediction logic
* Service behavior

### API Tests

Test:

* Registration
* Login
* Protected endpoints
* Flight search
* Assistant endpoint
* Conversation endpoints
* Prediction endpoint
* Recommendation endpoint

### Integration Tests

Verify important flows involving:

```text
FastAPI → Service → PostgreSQL
```

External APIs should be mocked in automated tests.

---

# 📅 Frozen 15-Phase Implementation Plan

### Phase 1 — Foundation

Create the clean project, FastAPI application, configuration, dependency management, health endpoint, and basic testing setup.

### Phase 2 — Database

Configure PostgreSQL, SQLAlchemy, Alembic, database session management, and core models.

### Phase 3 — Authentication

Implement registration, login, password hashing, JWT authentication, and protected routes.

### Phase 4 — Flight Provider

Implement the external flight-provider client and normalized flight data model.

### Phase 5 — Flight Search

Expose the flight-search REST API with validation, service logic, provider integration, and tests.

### Phase 6 — AI Understanding

Implement LLM integration, prompts, structured flight-intent extraction, and validation.

### Phase 7 — AI Assistant

Connect natural-language understanding with flight search and response generation.

### Phase 8 — Conversations

Persist conversations and messages and provide context-aware follow-up interactions.

### Phase 9 — Price Prediction

Implement a simple ML model, inference service, and prediction API.

### Phase 10 — Recommendations

Implement flight scoring, ranking, and recommendation explanations.

### Phase 11 — Preferences

Add user preferences and use them in recommendations.

### Phase 12 — Frontend Foundation

Create the React/TypeScript application and basic application structure.

### Phase 13 — Frontend Integration

Implement authentication, flight search, AI chat, predictions, recommendations, and conversation history.

### Phase 14 — Testing & Hardening

Add important unit/API/integration tests, validation, error handling, and security improvements.

### Phase 15 — Deployment & Portfolio Polish

Dockerize the complete application, clean configuration, improve README, add screenshots, verify the complete application, and prepare the project for GitHub/interviews.

---

# 🏁 Definition of Done

The project is complete when a user can:

```text
Register
   ↓
Login
   ↓
Search for flights
   ↓
Ask the AI assistant for flights naturally
   ↓
Receive real flight-provider results
   ↓
Ask follow-up questions
   ↓
Receive contextual answers
   ↓
View price prediction
   ↓
View recommended flights
   ↓
Save preferences
   ↓
Return later and view conversation history
```

The complete application must run locally using documented setup instructions and must have passing automated tests for its critical functionality.

---

# 📚 Portfolio Value

This project demonstrates that the developer can build a complete AI-powered application rather than only an isolated ML notebook or chatbot.

The main engineering story is:

```text
Python
  ↓
FastAPI
  ↓
REST APIs
  ↓
PostgreSQL
  ↓
External APIs
  ↓
LLM / NLP
  ↓
Machine Learning
  ↓
Recommendation System
  ↓
React
  ↓
Testing
  ↓
Docker
```

This makes the project suitable for demonstrating **Backend Engineering, AI Engineering, Python Development, and Applied Machine Learning** skills.

---

# 📌 Implementation Rule

The architecture described in this README is frozen.

During implementation:

* Do not redesign the architecture.
* Do not introduce unnecessary frameworks.
* Do not add new infrastructure without a strong reason.
* Do not create placeholder implementations.
* Do not leave TODO implementations.
* Do not modify unrelated modules.
* Keep services small and understandable.
* Prefer simple working code over sophisticated abstractions.
* Every phase must leave the project in a working state.
* Every phase must include appropriate tests.

The objective is not to build an enterprise system.

The objective is to build a **clean, working, explainable AI portfolio project quickly**.
