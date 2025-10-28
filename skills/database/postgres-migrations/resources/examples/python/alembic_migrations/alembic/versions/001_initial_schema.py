"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-10-27 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial users table"""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Create index
    op.create_index('idx_users_email', 'users', ['email'])


def downgrade() -> None:
    """Drop users table"""
    op.drop_index('idx_users_email', 'users')
    op.drop_table('users')
