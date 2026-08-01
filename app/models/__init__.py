from app.models.academic_year import AcademicYear
from app.models.base import Base
from app.models.school_class import SchoolClass
from app.models.lesson_schedule import LessonSchedule
from app.models.subject import Subject
from app.models.teacher import Teacher


__all__ = [
    "AcademicYear",
    "Base",
    "LessonSchedule",
    "SchoolClass",
    "Subject",
    "Teacher",
]