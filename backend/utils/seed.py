"""
utils/seed.py — Populates the providers table with mock Islamabad data.

Run inside the container:
    docker exec kidmat_backend python -m utils.seed

This gives the MatchingAgent real rows to work with so the full pipeline
(intent → matching → booking) can complete successfully.
"""

from core.database import SessionLocal
from models.provider import Provider, ServiceCategory


MOCK_PROVIDERS = [
    # ── AC Technicians ────────────────────────────────────────────────────────
    {
        "name": "Ali AC Services",
        "phone": "0300-1112233",
        "whatsapp_number": "0300-1112233",
        "city": "Islamabad",
        "category": ServiceCategory.AC_TECHNICIAN,
        "latitude": 33.6895,
        "longitude": 73.0551,
        "rating": 4.7,
        "reviews_count": 89,
        "description": "10+ years AC installation, repair & gas refill. Serving G-sectors.",
        "cnic": "61101-0000001-1",
    },
    {
        "name": "Cool Air Experts",
        "phone": "0311-9988776",
        "city": "Islamabad",
        "category": ServiceCategory.AC_TECHNICIAN,
        "latitude": 33.7001,
        "longitude": 73.0612,
        "rating": 4.4,
        "reviews_count": 55,
        "description": "Split & window AC specialists. Same-day service available.",
        "cnic": "61101-0000002-1",
    },

    # ── Plumbers ──────────────────────────────────────────────────────────────
    {
        "name": "Rehman Plumbing",
        "phone": "0321-4455667",
        "whatsapp_number": "0321-4455667",
        "city": "Islamabad",
        "category": ServiceCategory.PLUMBER,
        "latitude": 33.7215,
        "longitude": 73.0433,
        "rating": 4.5,
        "reviews_count": 62,
        "description": "Leak repairs, pipe fitting, water tank installation. F & I sectors.",
        "cnic": "61101-0000003-1",
    },
    {
        "name": "Master Plumbers CDA",
        "phone": "0345-7788990",
        "city": "Islamabad",
        "category": ServiceCategory.PLUMBER,
        "latitude": 33.7100,
        "longitude": 73.0500,
        "rating": 4.2,
        "reviews_count": 38,
        "cnic": "61101-0000004-1",
    },

    # ── Electricians ──────────────────────────────────────────────────────────
    {
        "name": "Karimi Electricals",
        "phone": "0333-6677889",
        "whatsapp_number": "0333-6677889",
        "city": "Islamabad",
        "category": ServiceCategory.ELECTRICIAN,
        "latitude": 33.6754,
        "longitude": 73.0667,
        "rating": 4.8,
        "reviews_count": 134,
        "description": "Wiring, load balancing, circuit breakers, WAPDA work. Licensed.",
        "cnic": "61101-0000005-1",
        "business_reg_number": "SECP-2019-ISB-4421",
    },
    {
        "name": "Voltage Pro Islamabad",
        "phone": "0312-5544332",
        "city": "Islamabad",
        "category": ServiceCategory.ELECTRICIAN,
        "latitude": 33.6900,
        "longitude": 73.0720,
        "rating": 4.3,
        "reviews_count": 47,
        "cnic": "61101-0000006-1",
    },

    # ── Carpenters ────────────────────────────────────────────────────────────
    {
        "name": "Hassan Carpentry",
        "phone": "0302-1122334",
        "city": "Islamabad",
        "category": ServiceCategory.CARPENTER,
        "latitude": 33.6981,
        "longitude": 73.0311,
        "rating": 4.3,
        "reviews_count": 47,
        "description": "Custom furniture, door fitting, kitchen cabinets.",
        "cnic": "61101-0000007-1",
    },
    {
        "name": "WoodCraft Islamabad",
        "phone": "0315-8899001",
        "city": "Islamabad",
        "category": ServiceCategory.CARPENTER,
        "latitude": 33.7050,
        "longitude": 73.0390,
        "rating": 4.6,
        "reviews_count": 73,
        "cnic": "61101-0000008-1",
    },

    # ── Cleaners ──────────────────────────────────────────────────────────────
    {
        "name": "CleanPro Islamabad",
        "phone": "0344-2233445",
        "whatsapp_number": "0344-2233445",
        "city": "Islamabad",
        "category": ServiceCategory.CLEANER,
        "latitude": 33.7102,
        "longitude": 73.0789,
        "rating": 4.6,
        "reviews_count": 201,
        "description": "Deep cleaning, sofa & carpet cleaning, post-construction cleanup.",
        "cnic": "61101-0000009-1",
        "business_reg_number": "SMEDA-2020-ISB-8812",
    },
    {
        "name": "Shine Home Services",
        "phone": "0323-3344556",
        "city": "Islamabad",
        "category": ServiceCategory.CLEANER,
        "latitude": 33.7200,
        "longitude": 73.0650,
        "rating": 4.1,
        "reviews_count": 88,
        "cnic": "61101-0000010-1",
    },

    # ── Painters ─────────────────────────────────────────────────────────────
    {
        "name": "ColorMaster Painters",
        "phone": "0301-9900112",
        "whatsapp_number": "0301-9900112",
        "city": "Islamabad",
        "category": ServiceCategory.PAINTER,
        "latitude": 33.6830,
        "longitude": 73.0480,
        "rating": 4.5,
        "reviews_count": 66,
        "description": "Interior & exterior painting, waterproofing, texture work.",
        "cnic": "61101-0000011-1",
    },
    {
        "name": "Pro Paint Islamabad",
        "phone": "0318-4455001",
        "city": "Islamabad",
        "category": ServiceCategory.PAINTER,
        "latitude": 33.6950,
        "longitude": 73.0530,
        "rating": 4.0,
        "reviews_count": 31,
        "cnic": "61101-0000012-1",
    },
]


def seed():
    db = SessionLocal()
    try:
        existing_count = db.query(Provider).count()
        if existing_count > 0:
            print(f"⚠️  Providers table already has {existing_count} rows. Skipping seed.")
            print("   (Delete existing rows first if you want to re-seed.)")
            return

        providers = [Provider(**data) for data in MOCK_PROVIDERS]
        db.add_all(providers)
        db.commit()
        print(f"✅  Seeded {len(providers)} mock providers into the database.")

        # Print a quick summary
        from collections import Counter
        cats = Counter(p.category.value for p in providers)
        for cat, count in sorted(cats.items()):
            print(f"   {cat}: {count} provider(s)")

    except Exception as e:
        db.rollback()
        print(f"❌  Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
