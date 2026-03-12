import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions.db import db


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user1_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    user2_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    matched_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────────
    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])

    messages = db.relationship(
        'Message', back_populates='match', lazy='dynamic',
        cascade='all, delete-orphan', order_by='Message.created_at.desc()',
    )

    # ── Constraints & Indexes ──────────────────────────────────────
    __table_args__ = (
        # Prevent duplicate matches: store the smaller UUID first
        # so (A,B) and (B,A) collapse into the same row.
        db.UniqueConstraint('user1_id', 'user2_id', name='uq_match_pair'),
        db.Index('ix_matches_user1', 'user1_id'),
        db.Index('ix_matches_user2', 'user2_id'),
        db.Index('ix_matches_is_active', 'is_active'),
    )

    def __repr__(self):
        return f'<Match {self.user1_id} ↔ {self.user2_id} active={self.is_active}>'
