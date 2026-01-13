import dataclasses
from enum import Enum

from asttimport.utils import clean_id


class ClassroomType(Enum):
    NORMAL = "normal"
    INFO = "info"
    GYM = "gym"
    SMALL = "small"
    MEDIA = "media"
    LAB = "lab"
    MEETING = "meeting"
    TEACHER = "teacher"
    SPECIAL = "special"
    DEVELOPMENT = "development"


@dataclasses.dataclass
class Teacher:
    name: str
    email: str

    @property
    def username(self):
        return self.email.split("@")[0]

    @property
    def id(self):
        return clean_id(f"T_{self.username}")

@dataclasses.dataclass
class Classroom:
    name: str
    type: ClassroomType
    @property
    def id(self):
        return clean_id(f"CR_{self.name}")

@dataclasses.dataclass
class Class:
    name: str
    grade: int
    teachers: list[Teacher]
    classroom: Classroom
    # groups: list[Group]

    @property
    def id(self):
        return clean_id(f"C_{self.name}")


# @dataclasses.dataclass
# class Subject:
#     name: str


@dataclasses.dataclass
class Assignment:
    subject: str
    teachers: list[Teacher]
    classroom_type: ClassroomType | None
    grade: int
    class_: Class | None
    group: str | None
    weekly_count: int
