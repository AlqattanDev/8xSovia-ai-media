"""add_url_local_path_constraints

Revision ID: f10b11038e4b
Revises: 13aaaeb95a70
Create Date: 2025-10-22 05:27:18.212984

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f10b11038e4b'
down_revision = '13aaaeb95a70'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add CHECK constraint to media_posts table to ensure only local URLs
    # Pattern explanation:
    # - ^https_/ : starts with https_/ (local format for downloaded Grok files)
    # - ^/ : starts with / (absolute local paths)
    # - NOT (^https?://) : does NOT start with http:// or https:// (blocks external URLs)
    op.create_check_constraint(
        'check_media_url_local',
        'media_posts',
        "media_url ~ '^https_/' OR media_url ~ '^/' OR NOT (media_url ~ '^https?://')"
    )

    # Add CHECK constraint to child_posts table to ensure only local URLs
    op.create_check_constraint(
        'check_media_url_local',
        'child_posts',
        "media_url ~ '^https_/' OR media_url ~ '^/' OR NOT (media_url ~ '^https?://')"
    )


def downgrade() -> None:
    # Remove CHECK constraints
    op.drop_constraint('check_media_url_local', 'child_posts', type_='check')
    op.drop_constraint('check_media_url_local', 'media_posts', type_='check')
