"""Seed the database with test users for discovery testing."""

import math
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from app import create_app
from app.extensions.db import db
from app.models.photo import UserPhoto
from app.models.user import User

app = create_app()

# ── Your user ID (update this to match your actual user) ──
MY_USER_ID = "a1e7bb7f-26a9-4555-beca-b7ff6aef3a1a"

# ── Base location: Nairobi, Kenya ─────────────────────────
BASE_LAT = -1.2921
BASE_LNG = 36.8219


def random_nearby(base_lat, base_lng, radius_km=30):
    """Return a random point within radius_km of the base."""
    r = radius_km / 111.32
    angle = random.uniform(0, 2 * math.pi)
    dist = random.uniform(0, r)
    lat = base_lat + dist * math.cos(angle)
    lng = base_lng + dist * math.sin(angle)
    return round(lat, 6), round(lng, 6)


def photo_url(name, idx=0):
    """Generate a deterministic placeholder avatar URL."""
    seed = name.replace(" ", "_").lower()
    colors = ["0D8ABC", "E91E63", "9C27B0", "4CAF50", "FF9800", "607D8B"]
    bg = colors[hash(seed) % len(colors)]
    return (
        f"https://ui-avatars.com/api/?name={seed}&size=512"
        f"&background={bg}&color=fff&bold=true&format=png"
    )


# ── Test user profiles ────────────────────────────────────
TEST_USERS = [
    {
        "display_name": "Amani Wanjiku",
        "gender": "female",
        "looking_for": "male",
        "bio": "Coffee lover | Travel enthusiast | Software developer by day, dancer by night",
        "dob": date(1998, 3, 15),
    },
    {
        "display_name": "Zuri Muthoni",
        "gender": "female",
        "looking_for": "male",
        "bio": "Bookworm | Yoga & meditation | Looking for genuine connections",
        "dob": date(1999, 7, 22),
    },
    {
        "display_name": "Liam Ochieng",
        "gender": "male",
        "looking_for": "female",
        "bio": "Football fanatic | Gym rat | Love cooking for someone special",
        "dob": date(1997, 11, 5),
    },
    {
        "display_name": "Aisha Kamau",
        "gender": "female",
        "looking_for": "everyone",
        "bio": "Artist | Music is my language | Let's explore Nairobi together",
        "dob": date(2000, 1, 30),
    },
    {
        "display_name": "Brian Kiprop",
        "gender": "male",
        "looking_for": "female",
        "bio": "Runner | Entrepreneur | Dog dad | Looking for my adventure partner",
        "dob": date(1996, 5, 18),
    },
    {
        "display_name": "Nyambura Njeri",
        "gender": "female",
        "looking_for": "male",
        "bio": "Chef in training | Netflix binger | Sunsets over city lights",
        "dob": date(2001, 9, 12),
    },
    {
        "display_name": "Daniel Mwangi",
        "gender": "male",
        "looking_for": "female",
        "bio": "Tech geek | Weekend hiker | Terrible at jokes but I try",
        "dob": date(1998, 12, 3),
    },
    {
        "display_name": "Faith Atieno",
        "gender": "female",
        "looking_for": "male",
        "bio": "Nurse by profession | Foodie | Love spontaneous road trips",
        "dob": date(1999, 4, 7),
    },
    {
        "display_name": "Kevin Otieno",
        "gender": "male",
        "looking_for": "everyone",
        "bio": "Photographer | Coffee snob | Always planning the next getaway",
        "dob": date(1997, 8, 25),
    },
    {
        "display_name": "Grace Wairimu",
        "gender": "female",
        "looking_for": "male",
        "bio": "Fashion designer | Cat mom | Swahili poetry enthusiast",
        "dob": date(2000, 6, 14),
    },
    {
        "display_name": "James Kimani",
        "gender": "male",
        "looking_for": "female",
        "bio": "Architect | Jazz lover | Weekend BBQ king",
        "dob": date(1995, 2, 28),
    },
    {
        "display_name": "Wambui Ndungu",
        "gender": "female",
        "looking_for": "male",
        "bio": "Law student | Debate champion | Looking for someone who can keep up",
        "dob": date(2001, 10, 20),
    },
    {
        "display_name": "Peter Njoroge",
        "gender": "male",
        "looking_for": "female",
        "bio": "DJ & music producer | Night owl | Your next favorite person",
        "dob": date(1998, 1, 11),
    },
    {
        "display_name": "Mercy Chebet",
        "gender": "female",
        "looking_for": "male",
        "bio": "Teacher | Marathon runner | Kindness is my superpower",
        "dob": date(1999, 3, 9),
    },
    {
        "display_name": "Alex Mutua",
        "gender": "male",
        "looking_for": "female",
        "bio": "Data scientist | Board game nerd | Trying to be a plant dad",
        "dob": date(1997, 7, 1),
    },
]


def seed():
    with app.app_context():
        # ── 1. Update your profile so it qualifies for discovery ──
        me = db.session.get(User, MY_USER_ID)
        if me:
            me.gender = me.gender or "male"
            me.looking_for = me.looking_for or "everyone"
            me.date_of_birth = me.date_of_birth or date(2000, 1, 1)
            me.latitude = BASE_LAT
            me.longitude = BASE_LNG
            me.last_active_at = datetime.now(timezone.utc)
            me.is_active = True
            print(f"Updated your profile: {me.display_name}")
        else:
            print(f"WARNING: Your user {MY_USER_ID} not found in DB.")
            print("Continuing to create test users anyway.\n")

        # ── 2. Create test users ─────────────────────────────────
        created = 0
        skipped = 0
        for profile in TEST_USERS:
            existing = User.query.filter_by(
                display_name=profile["display_name"]
            ).first()
            if existing:
                skipped += 1
                continue

            lat, lng = random_nearby(BASE_LAT, BASE_LNG)

            # Vary last_active_at so ranking produces a visible spread
            hours_ago = random.uniform(0, 120)
            last_active = datetime.now(timezone.utc) - timedelta(hours=hours_ago)

            user = User(
                id=uuid.uuid4(),
                firebase_uid=f"test_seed_{uuid.uuid4().hex[:12]}",
                display_name=profile["display_name"],
                gender=profile["gender"],
                looking_for=profile["looking_for"],
                bio=profile["bio"],
                date_of_birth=profile["dob"],
                latitude=lat,
                longitude=lng,
                last_active_at=last_active,
                is_active=True,
                is_verified=random.choice([True, False]),
                discovery_radius_km=50,
                age_min=18,
                age_max=50,
            )
            db.session.add(user)
            db.session.flush()

            # Add 1-2 placeholder photos per user
            num_photos = random.randint(1, 2)
            for i in range(num_photos):
                photo = UserPhoto(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    url=photo_url(profile["display_name"], i),
                    position=i,
                    is_primary=(i == 0),
                )
                db.session.add(photo)

            created += 1
            print(f"  Created {profile['display_name']:20s} "
                  f"({profile['gender']:10s}) "
                  f"at ({lat:.4f}, {lng:.4f}) "
                  f"active {hours_ago:.0f}h ago")

        db.session.commit()

        total = User.query.count()
        print(f"\nDone: {created} created, {skipped} skipped (already existed).")
        print(f"Total users in DB: {total}")


if __name__ == "__main__":
    seed()
