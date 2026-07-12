# Authentication APIs

Base Path

/api/v1/auth

---

## Register

POST /register

Description

Create a new user account.

Authentication

Not Required

Request

{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "StrongPassword123"
}

Response

201 Created

{
  "message": "User registered successfully",
  "user_id": "uuid"
}

---

## Login

POST /login

Description

Authenticate a user and return JWT tokens.

Authentication

Not Required

Response

200 OK

{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600
}

---

## Refresh Token

POST /refresh

Authentication

Refresh Token Required

Returns new access token.

---

## Logout

POST /logout

Authentication

JWT Required

Invalidates refresh token.

---

## Forgot Password

POST /forgot-password

Sends password reset email.

---

## Reset Password

POST /reset-password

Resets password using secure reset token.

---

## Verify Email

POST /verify-email

Verifies user email address.