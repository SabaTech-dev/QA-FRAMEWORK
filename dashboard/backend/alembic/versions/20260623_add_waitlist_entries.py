"""add waitlist_entries table

Revision ID: 20260623_waitlist
Revises: 20260329_onboarding
Create Date: 2026-06-23 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260623_waitlist'
down_revision = '20260329_onboarding'
branch_labels = None
depends_on = None


def upgrade():
    """Create waitlist_entries table"""
    op.create_table(
        'waitlist_entries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_waitlist_entries_email', 'waitlist_entries', ['email'], unique=True)
    op.create_index('ix_waitlist_entries_id', 'waitlist_entries', ['id'])
    op.create_index('ix_waitlist_entries_status', 'waitlist_entries', ['status'])


def downgrade():
    """Drop waitlist_entries table"""
    op.drop_index('ix_waitlist_entries_status', table_name='waitlist_entries')
    op.drop_index('ix_waitlist_entries_id', table_name='waitlist_entries')
    op.drop_index('ix_waitlist_entries_email', table_name='waitlist_entries')
    op.drop_table('waitlist_entries')
