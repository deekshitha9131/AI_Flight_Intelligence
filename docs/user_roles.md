# User Roles

## Overview

The AI Flight Intelligence Platform has two primary user roles. Each role has clearly defined responsibilities and permissions to ensure system security and maintainability.

---

# 1. Guest

A Guest is an unauthenticated visitor.

### Responsibilities

- View landing page
- Register an account
- Log in
- View public information
- Verify email
- Reset forgotten password

### Restrictions

- Cannot search flights
- Cannot access AI predictions
- Cannot save favorites
- Cannot access dashboards
- Cannot access admin features

---

# 2. User

A User is an authenticated traveler using the platform.

### Responsibilities

### Authentication

- Manage profile
- Change password
- Upload profile picture
- Logout

### Flight Search

- Search one-way flights
- Search round-trip flights
- Apply filters
- Sort search results

### AI Features

- Predict future flight prices
- Receive Buy Now / Wait recommendations
- View prediction confidence

### Recommendations

- Receive personalized flight recommendations
- Save favorite flights

### Dashboard

- View search history
- View travel statistics
- View favorite flights
- View prediction history

### Feedback

- Submit ratings
- Report issues

---

# 3. Admin

An Admin manages the platform and monitors system health.

### Responsibilities

### User Management

- View users
- Suspend users
- Delete users

### Analytics

- Monitor active users
- Monitor API usage
- Monitor prediction accuracy
- View popular routes

### Machine Learning

- Trigger model training
- Retrain models
- Compare models
- Monitor model performance

### Platform Management

- View logs
- Manage datasets
- Monitor external API health
- Review user feedback

---

# Permission Matrix

| Feature | Guest | User | Admin |
|----------|:----:|:----:|:----:|
| Register | ✓ | | |
| Login | ✓ | | |
| Search Flights | | ✓ | ✓ |
| Price Prediction | | ✓ | ✓ |
| Recommendations | | ✓ | ✓ |
| Favorites | | ✓ | ✓ |
| User Dashboard | | ✓ | ✓ |
| Admin Dashboard | | | ✓ |
| Train Models | | | ✓ |
| Manage Users | | | ✓ |
| View Analytics | | Limited | ✓ |