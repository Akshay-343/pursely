from sqlalchemy import create_engine

from alembic import context
from app import models  # noqa: F401
from app.core.config import settings
from app.core.db import Base

target_metadata = Base.metadata

with create_engine(settings.database_url).connect() as conn:
    context.configure(connection=conn, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
