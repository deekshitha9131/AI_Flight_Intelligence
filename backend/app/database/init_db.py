from app.database.session import check_database_connection


def initialize_database() -> bool:
    """Initialize the database layer by checking connectivity.

    This function intentionally performs only a connectivity probe and does not
    create any tables. Alembic remains responsible for schema migrations.
    """
    return check_database_connection()
