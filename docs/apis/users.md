# User APIs

Base Path

/api/v1/users

---

## Get Current User

GET /me

Returns authenticated user profile.

---

## Update Profile

PUT /me

Updates profile information.

---

## Change Password

PUT /change-password

Changes user password.

---

## Get Preferences

GET /preferences

Returns saved travel preferences.

---

## Update Preferences

PUT /preferences

Updates

- Budget
- Preferred airline
- Cabin
- Currency

---

## Favorites

GET /favorites

POST /favorites

DELETE /favorites/{id}