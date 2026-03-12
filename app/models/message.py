import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions.db import db


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('matches.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    sender_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    body = db.Column(db.Text, nullable=False)
    message_type = db.Column(
        db.String(20), nullable=False, default='text',
    )  # text, image, gif
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────────
    match = db.relationship('Match', back_populates='messages')
    sender = db.relationship('User', back_populates='sent_messages')

    # ── Indexes ────────────────────────────────────────────────────
    __table_args__ = (
        db.Index('ix_messages_match_created', 'match_id', 'created_at'),
        db.Index('ix_messages_is_read', 'match_id', 'is_read'),
    )

    def __repr__(self):
        return f'<Message {self.id} in match {self.match_id}>'
