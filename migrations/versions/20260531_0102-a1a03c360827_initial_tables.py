"""initial_tables

Revision ID: a1a03c360827
Revises: 
Create Date: 2026-05-31 01:02:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1a03c360827'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── chats ────────────────────────────────────────────────────────────────
    op.create_table(
        'chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'type',
            sa.Enum('private', 'group', name='chattype'),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'last_seen',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # ── chat_members ─────────────────────────────────────────────────────────
    op.create_table(
        'chat_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'joined_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── groups ───────────────────────────────────────────────────────────────
    op.create_table(
        'groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id'),
    )

    # ── messages ─────────────────────────────────────────────────────────────
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('delivered', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_messages_chat_id'), 'messages', ['chat_id'], unique=False)
    op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_messages_created_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_chat_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_table('groups')
    op.drop_table('chat_members')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('chats')
    op.execute("DROP TYPE IF EXISTS chattype")
