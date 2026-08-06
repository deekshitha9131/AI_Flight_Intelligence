"""User status.

Deliberately binary (active/inactive), not the three-state
active/suspended/deleted some earlier design notes sketched — account
deletion is already handled by `SoftDeleteMixin`'s `deleted_at`
(app/infrastructure/database/mixins.py). Folding "deleted" into this
enum as well would mean two different mechanisms both claiming to
represent "this account is gone," which invites exactly the kind of
inconsistency bug where one is updated and the other isn't. A user is
either active, temporarily inactive (suspended, self-deactivated,
whatever the reason), or soft-deleted — never more than one axis
encoding the same fact.

Defined once here, in the domain layer, and imported by both the
domain entity (app/domain/entities/user.py) and the ORM model
(app/infrastructure/database/models/user.py) — a single enum, not a
duplicated one at each layer, since the concept it represents genuinely
is the same thing.
"""

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
