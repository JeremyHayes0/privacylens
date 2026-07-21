"""add findings table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

finding_category_enum = sa.Enum(
    "https",
    "headers",
    "cookies",
    "trackers",
    "privacy_policy",
    "tos",
    "consent_banner",
    name="finding_category",
)
finding_type_enum = sa.Enum(
    "potential_issue",
    "observation",
    "detected_configuration",
    "recommendation",
    name="finding_type",
)
finding_severity_enum = sa.Enum("info", "low", "medium", "high", name="finding_severity")


def upgrade() -> None:
    bind = op.get_bind()
    finding_category_enum.create(bind, checkfirst=True)
    finding_type_enum.create(bind, checkfirst=True)
    finding_severity_enum.create(bind, checkfirst=True)

    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "scan_id",
            sa.Uuid(),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", finding_category_enum, nullable=False),
        sa.Column("finding_type", finding_type_enum, nullable=False),
        sa.Column("severity", finding_severity_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        # JSONB in Postgres for indexability; the ORM model uses the
        # portable sa.JSON().with_variant(JSONB(), "postgresql") type,
        # so this migration matches that at the DDL level.
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_findings_scan_id", "findings", ["scan_id"])
    op.create_index("ix_findings_category", "findings", ["category"])


def downgrade() -> None:
    op.drop_index("ix_findings_category", table_name="findings")
    op.drop_index("ix_findings_scan_id", table_name="findings")
    op.drop_table("findings")

    bind = op.get_bind()
    finding_severity_enum.drop(bind, checkfirst=True)
    finding_type_enum.drop(bind, checkfirst=True)
    finding_category_enum.drop(bind, checkfirst=True)
