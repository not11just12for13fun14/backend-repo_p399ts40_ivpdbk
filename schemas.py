"""
Database Schemas for the School LMS

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercased class name. Example: class Student -> "student" collection.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Student(BaseModel):
    name: str = Field(..., description="Full name of the student")
    email: str = Field(..., description="Unique email address")
    grade_level: str = Field(..., description="e.g., 9th, 10th, 11th, 12th")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")

class Lesson(BaseModel):
    title: str
    subject: str
    teacher: str
    description: Optional[str] = None
    date: datetime
    resources: Optional[List[str]] = None

class Scheduleitem(BaseModel):
    day: str = Field(..., description="Weekday name, e.g., Monday")
    start_time: str = Field(..., description="HH:MM in 24h format")
    end_time: str = Field(..., description="HH:MM in 24h format")
    subject: str
    room: Optional[str] = None

class Grade(BaseModel):
    subject: str
    assignment: str
    score: float
    total: float
    letter: Optional[str] = None
    date: datetime

class Assessment(BaseModel):
    title: str
    subject: str
    type: str = Field(..., description="Quiz, Test, Project, Exam")
    due_date: datetime
    status: str = Field("upcoming", description="upcoming, submitted, graded")

class Feedpost(BaseModel):
    author_name: str
    author_avatar: Optional[str] = None
    text: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime
    likes: int = 0
    comments_count: int = 0
