from enum import StrEnum


class DraftStatus(StrEnum):
    GENERATED = "generated"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"