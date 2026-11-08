"""Synthetic demo data. Every person, hospital and record here is FICTIONAL.

Usage:
    python -m app.db.seed           # seed an empty database
    python -m app.db.seed --reset   # wipe all rows first, then seed

Demo logins (password for all: Demo@123):
    admin@bloodbridge.demo                 Admin
    hospital@bloodbridge.demo              City General Hospital (Demo), Faisalabad
    hospital2@bloodbridge.demo             Lahore Demo Medical Centre
    donor@bloodbridge.demo                 O+ donor in Faisalabad (ranks near the top for O+)
    donor2@bloodbridge.demo                O- donor in Faisalabad (good for a decline demo)
"""
import random
import sys
from datetime import date, timedelta

from sqlalchemy import delete

from app.agents.orchestrator import approve_matches, handle_response, run_workflow
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import AgentRun, AuditLog, BloodRequest, Donor, DonorMatch, Hospital, Invitation, User
from app.services.geo import CITY_COORDS
from app.utils.time import utcnow

PASSWORD = "Demo@123"
rng = random.Random(42)

FIRST = ["Ali", "Ayesha", "Bilal", "Fatima", "Hamza", "Hira", "Imran", "Iqra", "Kamran", "Maryam",
         "Noman", "Sana", "Usman", "Zainab", "Farhan", "Rabia", "Saad", "Mehwish", "Tariq", "Anam",
         "Arjun", "Priya", "Rohan", "Sneha", "Vikram", "Neha", "Kabir", "Isha", "Danish", "Nida"]
LAST = ["Khan", "Ahmed", "Malik", "Hussain", "Raza", "Sheikh", "Butt", "Qureshi", "Chaudhry", "Iqbal",
        "Sharma", "Patel", "Das", "Mishra", "Nair"]

# Approximate population mix; rarer negatives still present so the demo has options.
GROUP_WEIGHTS = {"O+": 30, "B+": 27, "A+": 20, "AB+": 7, "O-": 5, "B-": 4, "A-": 4, "AB-": 3}
CLUSTERS = [("Faisalabad", 34), ("Lahore", 16), ("Jhang", 4), ("Chiniot", 4), ("Sargodha", 4)]


def _jitter(city: str, km: float) -> tuple[float, float]:
    lat, lon = CITY_COORDS[city.lower()]
    d = km / 111.0
    return round(lat + rng.uniform(-d, d), 5), round(lon + rng.uniform(-d, d), 5)


def _user(db, name, email, role):
    u = User(name=name, email=email, password_hash=hash_password(PASSWORD), role=role)
    db.add(u)
    db.flush()
    return u


def _donor(db, name, email, group, city, coords, availability="available", days_since=None,
           response_rate=0.5, status="eligible_demo"):
    u = _user(db, name, email, "donor")
    history = []
    last = None
    if days_since is not None:
        last = (date.today() - timedelta(days=days_since)).isoformat()
        history.append({"date": last, "location": city, "units": 1, "demo": True})
        if days_since < 500:
            history.append({"date": (date.today() - timedelta(days=days_since + 200)).isoformat(),
                            "location": city, "units": 1, "demo": True})
    db.add(Donor(
        user_id=u.id, blood_group=group, city=city, latitude=coords[0], longitude=coords[1],
        availability=availability,
        demo_eligibility={"status": status, "last_donation_date": last, "response_rate": response_rate,
                          "donation_history": history,
                          "note": "Synthetic demo field - not a medical eligibility decision"},
    ))


def reset(db) -> None:
    for model in (AuditLog, AgentRun, Invitation, DonorMatch, BloodRequest, Donor, Hospital, User):
        db.execute(delete(model))
    db.commit()


def seed(db) -> None:
    # Admin
    _user(db, "Demo Admin", "admin@bloodbridge.demo", "admin")

    # Hospitals
    h1u = _user(db, "Dr. Sara Malik (demo)", "hospital@bloodbridge.demo", "hospital")
    h1 = Hospital(user_id=h1u.id, name="City General Hospital (Demo)", city="Faisalabad",
                  latitude=31.4180, longitude=73.0790)
    h2u = _user(db, "Dr. Omar Raza (demo)", "hospital2@bloodbridge.demo", "hospital")
    h2 = Hospital(user_id=h2u.id, name="Lahore Demo Medical Centre", city="Lahore",
                  latitude=31.5497, longitude=74.3436)
    db.add_all([h1, h2])

    # Named demo donors with fixed, predictable properties
    _donor(db, "Ahmed Khan (demo)", "donor@bloodbridge.demo", "O+", "Faisalabad",
           (31.4520, 73.1300), days_since=300, response_rate=0.95)
    _donor(db, "Fatima Noor (demo)", "donor2@bloodbridge.demo", "O-", "Faisalabad",
           (31.4400, 73.1200), days_since=250, response_rate=0.9)

    # Random synthetic population
    groups, weights = list(GROUP_WEIGHTS), list(GROUP_WEIGHTS.values())
    n = 0
    for city, count in CLUSTERS:
        for _ in range(count):
            n += 1
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            roll = rng.random()
            availability = ("available" if roll < 0.75 else
                            "temporarily_unavailable" if roll < 0.9 else "unavailable")
            status = "deferred_demo" if rng.random() < 0.08 else "eligible_demo"
            days = rng.choice([None, rng.randint(20, 80), rng.randint(91, 700)])
            _donor(db, name, f"donor{n:03d}@bloodbridge.demo", rng.choices(groups, weights)[0], city,
                   _jitter(city, 12), availability, days, round(rng.uniform(0.2, 0.95), 2), status)
    db.commit()

    # Example requests, processed through the real agent workflow
    now = utcnow()
    r1 = BloodRequest(hospital_id=h2.id, title="REQ-DEMO-001 Elective surgery", blood_group="B+",
                      units_requested=1, urgency="normal", location="Lahore",
                      deadline=now + timedelta(days=2), description="Scheduled surgery, 1 unit B+.",
                      contact_info="Blood bank desk ext. 101 (demo)")
    r2 = BloodRequest(hospital_id=h1.id, title="REQ-DEMO-002 Ward stock top-up", blood_group="A+",
                      units_requested=2, urgency="normal", location="Faisalabad",
                      deadline=now + timedelta(days=3), description="Routine ward requirement.",
                      contact_info="Ward 4 nurse station (demo)")
    r3 = BloodRequest(hospital_id=h2.id, title="REQ-DEMO-003 Trauma case", blood_group="O+",
                      units_requested=2, urgency="urgent", location="Lahore",
                      deadline=now + timedelta(hours=8), description="Road traffic accident patient, 2 units O+.",
                      contact_info="Emergency desk (demo)")
    db.add_all([r1, r2, r3])
    db.commit()

    # r1: full cycle -> fulfilled (workflow state), gives analytics something to show
    run_workflow(db, r1, h2u.id)
    db.refresh(r1)
    top = sorted([m for m in r1.matches if m.status == "suggested"], key=lambda m: -m.match_score)[:2]
    approve_matches(db, r1, [m.id for m in top], [], h2u.id)
    db.refresh(r1)
    invs = sorted(r1.invitations, key=lambda i: i.sent_at)
    if len(invs) >= 2:
        handle_response(db, invs[0], "declined", "Sorry, travelling this week.", invs[0].donor.user_id)
        handle_response(db, invs[1], "accepted", None, invs[1].donor.user_id)
    # r3: analysed and matched, waiting for human approval
    run_workflow(db, r3, h2u.id)
    # r2 stays 'submitted' so the demo can run its workflow live


def main() -> None:
    db = SessionLocal()
    try:
        if "--reset" in sys.argv:
            reset(db)
            print("Wiped existing data.")
        elif db.query(User).first():
            print("Database already has data. Use --reset to wipe and reseed.")
            return
        seed(db)
        print(f"Seeded: {db.query(User).count()} users, {db.query(Donor).count()} donors, "
              f"{db.query(BloodRequest).count()} requests. Password for all demo logins: {PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
