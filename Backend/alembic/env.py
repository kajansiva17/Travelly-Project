from logging.config import fileConfig
from alembic import context
from sqlalchemy import text
from app.config import get_settings
from app.database import make_engine
from app.models import Base
from app import review_models  # register only the two approved dependency tables

config = context.config
if config.config_file_name:
    # Migrations may run in the application/test process. Preserve its audit
    # logger rather than silently disabling role decision/resubmission events.
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def run(connection):
    extension_tables = set()

    def include_name(name, type_, parent_names):
        # PostgreSQL extensions (for example PostGIS) own infrastructure tables.
        # Never propose dropping those while comparing the application schema.
        if type_ == 'table':
            schema = parent_names.get('schema_name') or connection.dialect.default_schema_name
            return (schema, name) not in extension_tables
        return True

    context.configure(connection=connection, target_metadata=Base.metadata,
                      version_table_schema=config.attributes.get('schema'), compare_type=True,
                      include_name=include_name)
    with context.begin_transaction():
        extension_tables.update(connection.execute(text("""
            SELECT n.nspname, c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = c.oid
            WHERE d.refclassid = 'pg_extension'::regclass AND d.deptype = 'e'
        """)).all())
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=get_settings().database_url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get('connection') is not None:
    run(config.attributes['connection'])
else:
    with make_engine().connect() as connection:
        run(connection)
