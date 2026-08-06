"""Project-wide constants.

Centralizing these here means the project name, API version prefix, and
pagination defaults are each defined exactly once. Any file needing them
imports from here rather than re-declaring a literal string, which is
what makes a future rename or version bump a one-line change instead of
a grep-and-replace across the codebase.
"""

from typing import Final

# --- Project identity ---
PROJECT_NAME: Final[str] = "AI Email Assistant Platform"
PROJECT_DESCRIPTION: Final[str] = (
    "An AI-native assistant that triages, understands, and drafts replies "
    "to Gmail email, with a human-approval gate on every outbound message."
)
PROJECT_VERSION: Final[str] = "0.1.0"

# --- API versioning ---
API_V1_PREFIX: Final[str] = "/api/v1"


# --- OpenAPI tag names ---
# Used to group endpoints in the generated docs. Declared centrally so a
# router and its tag metadata can never drift out of sync silently.
class OpenAPITags:
    HEALTH: Final[str] = "Health"
    AUTH: Final[str] = "Auth"
    THREADS: Final[str] = "Threads"
    DRAFTS: Final[str] = "Drafts"
    CONTACTS: Final[str] = "Contacts"
    SETTINGS: Final[str] = "Settings"
    NOTIFICATIONS: Final[str] = "Notifications"


OPENAPI_TAGS_METADATA: Final[list[dict[str, str]]] = [
    {
        "name": OpenAPITags.HEALTH,
        "description": "Liveness and readiness checks for orchestration and monitoring.",
    },
    {
        "name": OpenAPITags.AUTH,
        "description": "Google OAuth handshake and session management.",
    },
    {
        "name": OpenAPITags.THREADS,
        "description": "Email thread listing, filtering, and detail retrieval.",
    },
    {
        "name": OpenAPITags.DRAFTS,
        "description": "AI-generated draft replies and the human-approval workflow.",
    },
    {
        "name": OpenAPITags.CONTACTS,
        "description": "Contact records and per-contact relationship memory.",
    },
    {
        "name": OpenAPITags.SETTINGS,
        "description": "User-configurable preferences.",
    },
    {
        "name": OpenAPITags.NOTIFICATIONS,
        "description": "In-app notifications and unread state.",
    },
]

# --- Pagination defaults ---
DEFAULT_PAGE_SIZE: Final[int] = 25
MAX_PAGE_SIZE: Final[int] = 100

# --- Vector embeddings ---
# Dimensionality of the configured embedding model (text-embedding-3-small).
# pgvector columns are fixed-width — this must match whatever model
# EMBEDDING_MODEL (app/core/config.py) actually produces. If the model
# ever changes to one with a different output size, every existing
# embedding column and index needs a migration, not just this constant.
EMBEDDING_DIMENSIONS: Final[int] = 1536

# --- Health check status values ---
HEALTH_STATUS_OK: Final[str] = "ok"
HEALTH_STATUS_DEGRADED: Final[str] = "degraded"
HEALTH_STATUS_ERROR: Final[str] = "error"

# --- Standard response header ---
REQUEST_ID_HEADER: Final[str] = "X-Request-ID"

# --- Google OAuth ---
# Least-privilege by design (per the frozen security strategy): gmail
# scopes are readonly + send, never the broader "modify" or "full
# access" scopes, since nothing in this system needs to alter/delete
# mail in the user's mailbox. `openid` + the two userinfo scopes are
# what let the callback resolve a stable identity (`sub`) and a display
# email/name — without them Google's token response still succeeds but
# the userinfo endpoint has nothing to return.
GOOGLE_OAUTH_SCOPES: Final[list[str]] = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

GOOGLE_AUTHORIZATION_ENDPOINT: Final[str] = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT: Final[str] = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT: Final[str] = "https://www.googleapis.com/oauth2/v3/userinfo"

# --- Cookies ---
SESSION_COOKIE_NAME: Final[str] = "session_id"
# Short-lived, separate from the session cookie — holds the CSRF state
# value between the /login redirect and the /callback request only;
# cleared immediately once the callback validates it.
OAUTH_STATE_COOKIE_NAME: Final[str] = "oauth_state"
OAUTH_STATE_COOKIE_MAX_AGE_SECONDS: Final[int] = 600  # 10 minutes
