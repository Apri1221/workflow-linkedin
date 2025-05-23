"""Create model registery

Revision ID: 3a7b6d73f3f2
Revises: 
Create Date: 2024-06-14 14:19:11.806588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3a7b6d73f3f2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('model_registry',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('version', sa.String(length=50), nullable=False),
    sa.Column('type', sa.String(length=100), nullable=False),
    sa.Column('id', sa.String(length=36), server_default='uuid_generate_v4()', nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_registry_id'), 'model_registry', ['id'], unique=False)



def downgrade() -> None:

    op.drop_index(op.f('ix_model_registry_id'), table_name='model_registry')
    op.drop_table('model_registry')
    # ### end Alembic commands ###
