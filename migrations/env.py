from alembic import context
from codesynapse.db.models import Base
from codesynapse.db.session import engine

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
    connection.commit()
