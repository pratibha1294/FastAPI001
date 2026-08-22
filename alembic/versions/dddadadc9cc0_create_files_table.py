"""Create files table

Revision ID: dddadadc9cc0
Revises: 8a0fc16d5a33
Create Date: 2026-08-22 19:17:22.445275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dddadadc9cc0'
down_revision: Union[str, Sequence[str], None] = '8a0fc16d5a33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
            """
            CREATE TABLE files (
                id INT AUTO_INCREMENT PRIMARY KEY,
                owner_id INT NOT NULL, 
                filename VARCHAR(255) NOT NULL,
                storage_key VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
    )
    


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE files")
    
