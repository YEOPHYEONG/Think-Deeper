# alembic/versions/abcdef123456_add_session_state_and_transcript.py

"""add session_state and session_transcript tables

Revision ID: abcdef123456
Revises: d9fd2944ebb2
Create Date: 2025-05-05 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'abcdef123456'
down_revision = 'd9fd2944ebb2'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'session_state',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('state', postgresql.JSONB, nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_table(
        'session_transcript',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('session_state.session_id')),
        sa.Column('occurred_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
    )

def downgrade():
    op.drop_table('session_transcript')
    op.drop_table('session_state')
