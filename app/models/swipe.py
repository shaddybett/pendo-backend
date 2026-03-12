import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions.db import db


class Swipe(db.Model):
    __tablename__ = 'swipes'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    swiper_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    target_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    direction = db.Column(
        db.String(20), nullable=False,
    )  # like, dislike, super_like
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────────
    swiper = db.relationship(
        'User', foreign_keys=[swiper_id], back_populates='swipes_made',
    )
    target = db.relationship(
        'User', foreign_keys=[target_user_id], back_populates='swipes_received',
    )

    # ── Constraints & Indexes ──────────────────────────────────────
    __table_args__ = (
        # Prevent duplicate swipes: one user can swipe on another only once
        db.UniqueConstraint('swiper_id', 'target_user_id',
                            name='uq_swipe_pair'),
        db.Index('ix_swipes_swiper', 'swiper_id'),
        db.Index('ix_swipes_target', 'target_user_id'),
        db.Index('ix_swipes_direction', 'direction'),
    )

    def __repr__(self):
        return f'<Swipe {self.swiper_id} → {self.target_user_id} ({self.direction})>'
