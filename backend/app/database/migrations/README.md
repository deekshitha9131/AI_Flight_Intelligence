# Alembic migrations

This directory contains Alembic migration assets for the backend.

## Commands

Create a new migration:

```bash
alembic revision --autogenerate -m "describe_changes"
```

Apply pending migrations:

```bash
alembic upgrade head
```

Downgrade one revision:

```bash
alembic downgrade -1
```

View migration history:

```bash
alembic history
```

View the current revision:

```bash
alembic current
```

## Notes

- The migration environment reads the database URL from the application's settings object.
- Future ORM models will be discovered via the shared declarative base in app.database.base.
- No ORM models are created in this step; Alembic is prepared for the next phase.
