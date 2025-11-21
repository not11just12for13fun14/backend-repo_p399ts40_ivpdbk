import os
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import (
    Student as StudentSchema,
    Lesson as LessonSchema,
    Scheduleitem as ScheduleItemSchema,
    Grade as GradeSchema,
    Assessment as AssessmentSchema,
    Feedpost as FeedPostSchema,
)

app = FastAPI(title="School LMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "School LMS API is running"}


# -------------- Helpers --------------

def _collection(name: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    return db[name]


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    # Convert datetimes to isoformat
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# -------------- Models for requests --------------

class CreateLesson(BaseModel):
    title: str
    subject: str
    teacher: str
    description: Optional[str] = None
    date: datetime
    resources: Optional[List[str]] = None


class CreateScheduleItem(BaseModel):
    day: str
    start_time: str
    end_time: str
    subject: str
    room: Optional[str] = None


class CreateGrade(BaseModel):
    subject: str
    assignment: str
    score: float
    total: float
    letter: Optional[str] = None
    date: datetime


class CreateAssessment(BaseModel):
    title: str
    subject: str
    type: str
    due_date: datetime
    status: str = "upcoming"


class CreateFeedPost(BaseModel):
    author_name: str
    author_avatar: Optional[str] = None
    text: Optional[str] = None
    image_url: Optional[str] = None


# -------------- Endpoints --------------

@app.get("/api/feed")
async def list_feed(limit: int = 20):
    docs = get_documents("feedpost", {}, limit)
    docs = sorted(docs, key=lambda d: d.get("created_at", datetime.min), reverse=True)
    return [_serialize(d) for d in docs]


@app.post("/api/feed")
async def create_feed(item: CreateFeedPost):
    data = FeedPostSchema(
        author_name=item.author_name,
        author_avatar=item.author_avatar,
        text=item.text,
        image_url=item.image_url,
        created_at=datetime.utcnow(),
        likes=0,
        comments_count=0,
    )
    inserted_id = create_document("feedpost", data)
    doc = _collection("feedpost").find_one({"_id": __import__("bson").ObjectId(inserted_id)})
    return _serialize(doc)


@app.get("/api/schedule")
async def list_schedule():
    docs = get_documents("scheduleitem", {})
    # Keep a stable order: Mon..Sun by custom order map + start_time
    order = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    docs = sorted(
        docs,
        key=lambda d: (
            order.get(str(d.get("day", "")).lower(), 7),
            str(d.get("start_time", ""))
        ),
    )
    return [_serialize(d) for d in docs]


@app.post("/api/schedule")
async def create_schedule(item: CreateScheduleItem):
    data = ScheduleItemSchema(**item.model_dump())
    inserted_id = create_document("scheduleitem", data)
    doc = _collection("scheduleitem").find_one({"_id": __import__("bson").ObjectId(inserted_id)})
    return _serialize(doc)


@app.get("/api/lessons")
async def list_lessons(limit: int = 50):
    docs = get_documents("lesson", {}, limit)
    docs = sorted(docs, key=lambda d: d.get("date", datetime.min), reverse=True)
    return [_serialize(d) for d in docs]


@app.post("/api/lessons")
async def create_lesson(item: CreateLesson):
    data = LessonSchema(**item.model_dump())
    inserted_id = create_document("lesson", data)
    doc = _collection("lesson").find_one({"_id": __import__("bson").ObjectId(inserted_id)})
    return _serialize(doc)


@app.get("/api/grades")
async def list_grades(limit: int = 100):
    docs = get_documents("grade", {}, limit)
    docs = sorted(docs, key=lambda d: d.get("date", datetime.min), reverse=True)
    return [_serialize(d) for d in docs]


@app.post("/api/grades")
async def create_grade(item: CreateGrade):
    data = GradeSchema(**item.model_dump())
    inserted_id = create_document("grade", data)
    doc = _collection("grade").find_one({"_id": __import__("bson").ObjectId(inserted_id)})
    return _serialize(doc)


@app.get("/api/assessments")
async def list_assessments(limit: int = 50):
    docs = get_documents("assessment", {}, limit)
    docs = sorted(docs, key=lambda d: d.get("due_date", datetime.min))
    return [_serialize(d) for d in docs]


@app.post("/api/assessments")
async def create_assessment(item: CreateAssessment):
    data = AssessmentSchema(**item.model_dump())
    inserted_id = create_document("assessment", data)
    doc = _collection("assessment").find_one({"_id": __import__("bson").ObjectId(inserted_id)})
    return _serialize(doc)


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, "name", "✅ Connected")
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.post("/seed")
async def seed_demo_data():
    """Populate the database with sample content for quick demo."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Avoid duplicate seeding
    if _collection("feedpost").count_documents({}) > 0:
        return {"status": "ok", "message": "Already seeded"}

    now = datetime.utcnow()

    # Feed
    posts = [
        FeedPostSchema(author_name="Ms. Carter", text="Welcome back to the new term!", image_url=None, created_at=now - timedelta(hours=2), likes=12, comments_count=3),
        FeedPostSchema(author_name="Sports Dept.", text="Tryouts start Monday. Go Blue Hawks!", image_url=None, created_at=now - timedelta(days=1), likes=48, comments_count=9),
        FeedPostSchema(author_name="Science Club", text="Lab safety workshop tomorrow.", image_url=None, created_at=now - timedelta(days=2), likes=20, comments_count=4),
    ]
    for p in posts:
        create_document("feedpost", p)

    # Schedule (Mon-Fri)
    schedule = [
        ScheduleItemSchema(day="Monday", start_time="08:00", end_time="08:50", subject="Math", room="A101"),
        ScheduleItemSchema(day="Monday", start_time="09:00", end_time="09:50", subject="English", room="B203"),
        ScheduleItemSchema(day="Tuesday", start_time="10:00", end_time="10:50", subject="Chemistry", room="Lab 2"),
        ScheduleItemSchema(day="Wednesday", start_time="11:00", end_time="11:50", subject="History", room="C305"),
        ScheduleItemSchema(day="Thursday", start_time="13:00", end_time="13:50", subject="Physics", room="Lab 1"),
        ScheduleItemSchema(day="Friday", start_time="14:00", end_time="14:50", subject="Art", room="D110"),
    ]
    for s in schedule:
        create_document("scheduleitem", s)

    # Lessons
    lessons = [
        LessonSchema(title="Quadratic Functions", subject="Math", teacher="Mr. Lee", description="Parabolas and vertex form", date=now - timedelta(days=1), resources=["slides.pdf", "practice.docx"]),
        LessonSchema(title="Poetry Analysis", subject="English", teacher="Ms. Carter", description="Figurative language", date=now - timedelta(days=2), resources=["poems.pdf"]),
    ]
    for l in lessons:
        create_document("lesson", l)

    # Grades
    grades = [
        GradeSchema(subject="Math", assignment="Algebra Quiz", score=18, total=20, letter="A", date=now - timedelta(days=3)),
        GradeSchema(subject="English", assignment="Essay Draft", score=45, total=50, letter="A-", date=now - timedelta(days=4)),
    ]
    for g in grades:
        create_document("grade", g)

    # Assessments
    assessments = [
        AssessmentSchema(title="Chemistry Lab Report", subject="Chemistry", type="Project", due_date=now + timedelta(days=2), status="upcoming"),
        AssessmentSchema(title="Physics Midterm", subject="Physics", type="Exam", due_date=now + timedelta(days=10), status="upcoming"),
    ]
    for a in assessments:
        create_document("assessment", a)

    return {"status": "ok", "message": "Seeded demo content"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
