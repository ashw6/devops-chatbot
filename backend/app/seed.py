"""Setup script: creates departments, the administrator account and (optionally) demo data.
Run manually with:  python -m app.seed
NOTE: the FAQ entries below are SAMPLE data. Replace them with your college's real information."""
from sqlalchemy.orm import Session
from .config import settings
from .database import Base, SessionLocal, engine
from .models import Department, FAQEntry, User
from .security import hash_password

DEPARTMENTS = ["Admissions", "Accounts", "Examination", "Academics", "Hostel", "Administration"]

SAMPLE_FAQS = [
    ("Admissions", "What documents are required for admission?",
     "Bring your 10th and 12th mark sheets, transfer certificate, entrance exam rank card, Aadhaar card, "
     "four passport-size photographs and the caste or income certificate if you are claiming a concession."),
    ("Admissions", "When is the last date to apply for admission? What is the admission deadline?",
     "Applications for the first year close on 30 June. Late applications are considered only if seats remain."),
    ("Admissions", "How can I check my admission application status?",
     "Log in to the admissions portal with your application number. The status changes to Verified once your "
     "documents are checked by the admissions office."),
    ("Fees", "What is the last date to pay the semester fee? What is the fee deadline?",
     "The semester fee must be paid within the first 15 days after the semester starts. A late fine of Rs. 100 "
     "per day applies after that."),
    ("Fees", "How do I pay my college fee online?",
     "Open the student portal, choose Fee Payment, select the semester and pay by UPI, net banking or card. "
     "Download the receipt after the payment succeeds."),
    ("Fees", "Can I pay the fee in instalments?",
     "Instalments are allowed only with written approval from the Accounts section. Raise a query with the "
     "category Fees and explain your situation."),
    ("Scholarship", "How do I apply for a scholarship?",
     "Scholarship applications open in August. Submit the income certificate, previous marks and bank details "
     "to the Accounts section through the scholarship form on the portal."),
    ("Examination", "When are the semester examinations held? What is the exam schedule?",
     "End-semester examinations are held in November and April. The detailed timetable is published on the "
     "notice board and the portal two weeks before the exams."),
    ("Examination", "How do I download my hall ticket?",
     "Hall tickets are available on the student portal under Examinations one week before the exam. "
     "Fee dues must be cleared first."),
    ("Examination", "How can I apply for revaluation or re-totalling?",
     "Apply within 7 days of result declaration through the portal and pay the revaluation fee per paper. "
     "Revised marks are published in about three weeks."),
    ("Academics", "What is the minimum attendance required to write the exams?",
     "Students need at least 75% attendance in each course. Between 65% and 75% requires condonation with a "
     "medical certificate and a fee."),
    ("Academics", "Where can I find my class timetable?",
     "The timetable is on the student portal under Academics and on the department notice board. "
     "Changes are announced by the class coordinator."),
    ("Hostel", "How do I apply for a hostel room?",
     "Fill the hostel application form on the portal, pay the hostel deposit and submit a copy of the receipt "
     "to the hostel office. Rooms are allotted by seniority and distance from home."),
    ("Hostel", "What are the hostel in-time and out-time rules?",
     "Hostel gates close at 9:00 PM. Weekend outings require the warden's permission slip and a parent's "
     "confirmation."),
    ("Certificates", "How do I get a bonafide certificate?",
     "Request it from the administrative office with your ID card and the purpose of the certificate. "
     "It is normally ready in two working days."),
    ("Certificates", "How do I get a transfer certificate or migration certificate?",
     "Submit the no-dues form signed by the library, hostel and accounts sections to the administrative office. "
     "Processing takes about one week."),
    ("Other", "What are the library timings?",
     "The central library is open from 8:30 AM to 8:00 PM on working days and 9:00 AM to 1:00 PM on Saturdays."),
    ("Other", "Who do I contact for placement information?",
     "The Training and Placement cell handles all placement activity. Register on the placement portal and "
     "watch the notice board for company visit schedules."),
]


def seed(db: Session):
    if db.query(Department).count() == 0:
        db.add_all(Department(name=n) for n in DEPARTMENTS)
        db.flush()
    if not db.query(User).filter(User.role == "admin").first():
        db.add(User(full_name="College Administrator", email=settings.ADMIN_EMAIL.lower(),
                    password_hash=hash_password(settings.ADMIN_PASSWORD), role="admin"))
    if settings.SEED_DEMO:
        if not db.query(User).filter(User.role == "staff").first():
            for d in db.query(Department):
                slug = d.name.lower()
                db.add(User(full_name=f"{d.name} Staff", email=f"staff.{slug}@college.edu",
                            password_hash=hash_password("Staff@123"), role="staff", department_id=d.id))
        if not db.query(User).filter(User.email == "student@college.edu").first():
            db.add(User(full_name="Demo Student", email="student@college.edu",
                        password_hash=hash_password("Student@123"), role="student"))
        if db.query(FAQEntry).count() == 0:
            db.add_all(FAQEntry(category=c, question=q, answer=a, source_doc=f"{c} Circular (sample)")
                       for c, q, a in SAMPLE_FAQS)
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed(session)
    print("Seed complete. Admin:", settings.ADMIN_EMAIL)
