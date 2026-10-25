"""Database migration environment for AirportOps ORM metadata."""
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.db import Base, DATABASE_URL
from app import models as core_models
from app.operations import models as operations_models

config = context.config
config.set_main_option('sqlalchemy.url', DATABASE_URL.replace('%','%%'))
target_metadata = Base.metadata

def offline():
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction(): context.run_migrations()

def online():
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                    prefix='sqlalchemy.', poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=connection.dialect.name == 'sqlite')
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): offline()
else: online()
