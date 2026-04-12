"""Peewee migrations -- 019_add_curator_job_dataset_fields.py

Adds dataset_name and created_knowledge_id columns to the curator_job table.
These support the KB-to-Dataset finalization workflow: when a curator job
completes, a Knowledge (dataset) record is created and linked back to the job.

Uses raw SQL because curator_job was created by SQLAlchemy, not peewee,
so it is not in the peewee migrator's model registry.
"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.sql(
        "ALTER TABLE curator_job "
        "ADD COLUMN IF NOT EXISTS dataset_name TEXT, "
        "ADD COLUMN IF NOT EXISTS created_knowledge_id TEXT;"
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.sql(
        "ALTER TABLE curator_job "
        "DROP COLUMN IF EXISTS dataset_name, "
        "DROP COLUMN IF EXISTS created_knowledge_id;"
    )
