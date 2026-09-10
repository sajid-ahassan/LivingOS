from sqlalchemy import text

from app.database import engine


ALLOWED_STATES = (
    "OPEN",
    "ACTIVE",
    "ASSIGNED",
    "DISABLED",
    "REVOKED",
    "RETURN_REQUESTED",
    "RETURNED",
    "REASSIGNED",
)


def main() -> None:
    with engine.begin() as connection:
        constraints = connection.execute(
            text(
                """
                SELECT constraint_record.conname
                FROM pg_constraint AS constraint_record
                JOIN pg_class AS table_record
                  ON table_record.oid = constraint_record.conrelid
                JOIN pg_namespace AS schema_record
                  ON schema_record.oid = table_record.relnamespace
                WHERE schema_record.nspname = 'public'
                  AND table_record.relname = 'company_resources'
                  AND constraint_record.contype = 'c'
                  AND pg_get_constraintdef(constraint_record.oid) ILIKE '%status%'
                """
            )
        ).scalars().all()

        for constraint_name in constraints:
            quoted_name = connection.dialect.identifier_preparer.quote(constraint_name)
            connection.exec_driver_sql(
                f"ALTER TABLE company_resources DROP CONSTRAINT {quoted_name}"
            )

        allowed_values = ", ".join(f"'{value}'" for value in ALLOWED_STATES)
        connection.exec_driver_sql(
            "ALTER TABLE company_resources "
            "ADD CONSTRAINT ck_company_resources_status "
            f"CHECK (status IN ({allowed_values}))"
        )

    print("company_resources now accepts the OPEN resource state.")


if __name__ == "__main__":
    main()
