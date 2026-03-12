import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions.db import db


class UserPhoto(db.Model):
    __tablename__ = 'user_photos'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    url = db.Column(db.String(512), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────────
    user = db.relationship('User', back_populates='photos')

    # ── Indexes ────────────────────────────────────────────────────
    __table_args__ = (
        db.Index('ix_user_photos_user_position', 'user_id', 'position'),
    )

    def __repr__(self):
        return f'<UserPhoto {self.id} pos={self.position}>'
