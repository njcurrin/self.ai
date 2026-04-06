"""Create benchmark_config table and seed known benchmarks

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-05 00:00:00.000000

"""

import time
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Text, Integer, BigInteger

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None

# Seed: all known benchmarks with a conservative 120-minute default.
# Admins can adjust max_duration_minutes per benchmark after running real evals.
SEED_BENCHMARKS = [
    # lm-eval benchmarks
    ("hellaswag",       "lm-eval"),
    ("mmlu",            "lm-eval"),
    ("arc_easy",        "lm-eval"),
    ("arc_challenge",   "lm-eval"),
    ("winogrande",      "lm-eval"),
    ("truthfulqa_mc",   "lm-eval"),
    ("gsm8k",           "lm-eval"),
    ("boolq",           "lm-eval"),
    ("piqa",            "lm-eval"),
    ("openbookqa",      "lm-eval"),
    ("sciq",            "lm-eval"),
    ("logiqa",          "lm-eval"),
    ("mathqa",          "lm-eval"),
    ("copa",            "lm-eval"),
    # bigcode benchmarks
    ("humaneval",       "bigcode"),
    ("mbpp",            "bigcode"),
    ("apps",            "bigcode"),
    ("multiple_e",      "bigcode"),
    ("ds1000",          "bigcode"),
    ("humanevalpack",   "bigcode"),
    ("mbpp_plus",       "bigcode"),
    ("humaneval_plus",  "bigcode"),
]


def upgrade():
    print("Creating benchmark_config table")
    op.create_table(
        "benchmark_config",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("benchmark", sa.Text(), nullable=False),
        sa.Column("eval_type", sa.Text(), nullable=False),
        sa.Column("max_duration_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    print("Seeding benchmark_config with default benchmarks")
    bc = table(
        "benchmark_config",
        column("id", Text),
        column("benchmark", Text),
        column("eval_type", Text),
        column("max_duration_minutes", Integer),
        column("notes", Text),
        column("created_at", BigInteger),
        column("updated_at", BigInteger),
    )

    # Check which (benchmark, eval_type) pairs already exist (idempotent)
    conn = op.get_bind()
    existing = set(
        conn.execute(
            sa.text("SELECT benchmark || '|' || eval_type FROM benchmark_config")
        ).scalars()
    )

    now = int(time.time())
    rows = []
    for benchmark, eval_type in SEED_BENCHMARKS:
        key = f"{benchmark}|{eval_type}"
        if key not in existing:
            rows.append({
                "id": str(uuid.uuid4()),
                "benchmark": benchmark,
                "eval_type": eval_type,
                "max_duration_minutes": 120,
                "notes": None,
                "created_at": now,
                "updated_at": now,
            })

    if rows:
        op.bulk_insert(bc, rows)


def downgrade():
    op.drop_table("benchmark_config")
