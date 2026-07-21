"""add organizations, targets, scans; link users to organizations

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-19

"""
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

scan_status_enum = sa.Enum("queued", "running", "completed", "failed", name="scan_status")


def upgrade() -> None:
    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- users.organization_id ---
    # Added nullable first: this migration must stay safe to run
    # against a `users` table that already has rows (a fresh install
    # has none, but a real deployment might). Existing users are
    # backfilled into a single placeholder organization, and only then
    # is the column tightened to NOT NULL -- doing it in one step would
    # fail immediately against any pre-existing row.
    op.add_column("users", sa.Column("organization_id", sa.Uuid(), nullable=True))

    connection = op.get_bind()
    existing_user_count = connection.execute(sa.text("SELECT COUNT(*) FROM users")).scalar_one()
    if existing_user_count:
        legacy_org_id = uuid.uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO organizations (id, name, created_at) "
                "VALUES (:id, :name, now())"
            ),
            {"id": legacy_org_id, "name": "Legacy Organization"},
        )
        connection.execute(
            sa.text("UPDATE users SET organization_id = :org_id WHERE organization_id IS NULL"),
            {"org_id": legacy_org_id},
        )

    op.alter_column("users", "organization_id", nullable=False)
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_foreign_key(
        "fk_users_organization_id",
        "users",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- targets ---
    op.create_table(
        "targets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_targets_organization_id", "targets", ["organization_id"])

    # --- scans ---
    scan_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "scans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "target_id",
            sa.Uuid(),
            sa.ForeignKey("targets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "triggered_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", scan_status_enum, nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_scans_target_id", "scans", ["target_id"])
    op.create_index("ix_scans_status", "scans", ["status"])


def downgrade() -> None:
    op.drop_index("ix_scans_status", table_name="scans")
    op.drop_index("ix_scans_target_id", table_name="scans")
    op.drop_table("scans")
    scan_status_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_targets_organization_id", table_name="targets")
    op.drop_table("targets")

    op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_column("users", "organization_id")

    op.drop_table("organizations")
