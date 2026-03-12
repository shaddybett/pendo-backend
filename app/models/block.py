import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions.db import db


class Block(db.Model):
    __tablename__ = 'blocks'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    blocked_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────────
    blocker = db.relationship(
        'User', foreign_keys=[blocker_id], back_populates='blocks_made',
    )
    blocked = db.relationship(
        'User', foreign_keys=[blocked_id], back_populates='blocks_received',
    )

    # ── Constraints & Indexes ──────────────────────────────────────
    __table_args__ = (
        # A user can only block another user once
        db.UniqueConstraint('blocker_id', 'blocked_id', name='uq_block_pair'),
        db.Index('ix_blocks_blocker', 'blocker_id'),
        db.Index('ix_blocks_blocked', 'blocked_id'),
    )

    def __repr__(self):
        return f'<Block {self.blocker_id} → {self.blocked_id}>'
