import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions.db import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firebase_uid = db.Column(db.String(128), unique=True,
                             nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False, default='')
    email = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    # if profile_completed == False → show onboarding 
    profile_completed = db.Column(db.Boolean, nullable=False, default=False)
    # male, female, non-binary
    gender = db.Column(db.String(20), nullable=True)
    # male, female, everyone
    looking_for = db.Column(db.String(20), nullable=True)

    # Discovery preferences
    discovery_radius_km = db.Column(db.Integer, nullable=True, default=50)
    age_min = db.Column(db.Integer, nullable=True, default=18)
    age_max = db.Column(db.Integer, nullable=True, default=45)

    # Location
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Status flags
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)

    # Timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_active_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Relationships ──────────────────────────────────────────────
    photos = db.relationship(
        'UserPhoto', back_populates='user', lazy='dynamic',
        cascade='all, delete-orphan', order_by='UserPhoto.position',
    )

    swipes_made = db.relationship(
        'Swipe', foreign_keys='Swipe.swiper_id',
        back_populates='swiper', lazy='dynamic',
    )
    swipes_received = db.relationship(
        'Swipe', foreign_keys='Swipe.target_user_id',
        back_populates='target', lazy='dynamic',
    )

    sent_messages = db.relationship(
        'Message', back_populates='sender', lazy='dynamic',
    )

    blocks_made = db.relationship(
        'Block', foreign_keys='Block.blocker_id',
        back_populates='blocker', lazy='dynamic',
    )
    blocks_received = db.relationship(
        'Block', foreign_keys='Block.blocked_id',
        back_populates='blocked', lazy='dynamic',
    )

    # ── Indexes ────────────────────────────────────────────────────
    __table_args__ = (
        db.Index('ix_users_gender', 'gender'),
        db.Index('ix_users_is_active', 'is_active'),
        db.Index('ix_users_location', 'latitude', 'longitude'),
    )

    def __repr__(self):
        return f'<User {self.display_name} ({self.id})>'
