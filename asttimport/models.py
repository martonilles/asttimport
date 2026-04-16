import dataclasses
import uuid
from enum import Enum

from asttimport.utils import clean_id


# TIMESLOTS = dict[int, dict[int, str]]
TIMESLOTS = str


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
    timeslots: TIMESLOTS

    @property
    def username(self):
        if self.email:
            return self.email.split("@")[0]

        return "".join([p[:3] for p in self.name.split(" ")])

    @property
    def id(self):
        return clean_id(f"T_{self.username}")


@dataclasses.dataclass
class Classroom:
    name: str
    type: str
    timeslots: TIMESLOTS

    @property
    def id(self):
        return clean_id(f"CR_{self.name}")


@dataclasses.dataclass
class Class:
    ref_name: str
    name: str
    grade: int
    teachers: list[Teacher]
    classroom: Classroom | None
    timeslots: TIMESLOTS

    @property
    def id(self):
        return clean_id(f"C_{self.name}")

    def __hash__(self):
        return hash(self.id)


@dataclasses.dataclass
class MetaClass:
    ref_name: str
    grade: int
    class_names: list[str]
    classes: list[Class]


@dataclasses.dataclass
class Subject:
    name: str
    timeslots: TIMESLOTS

    @property
    def id(self):
        return clean_id(f"S_{self.name}")


@dataclasses.dataclass
class Group:
    name: str
    class_: Class

    @property
    def base(self):
        return self.name.split("/")[0]

    @property
    def id(self):
        return clean_id(f"G_{self.class_.grade}_{self.class_.name}_{self.name}")

    def __hash__(self):
        return hash(self.id)


class Term(Enum):
    FULL = "11"
    FIRST = "10"
    SECOND = "01"

@dataclasses.dataclass
class Assignment:
    subject: Subject
    teachers: list[Teacher]
    classroom_type: str | None
    classes: list[Class]
    groups: list[Group]
    weekly_count: int
    double_count: int = 0
    active_day_count: int = 0
    term: Term = dataclasses.field(default=Term.FULL)
    classroom_count: int = 1
    _id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)

    def __post_init__(self):
        if self.classes is None and not self.groups:
            raise ValueError(
                f"Assignment must have at least one group when class is not set: {self}"
            )

    @property
    def key(self):
        key = [
            self.subject.name,
            *[c.name for c in self.classes],
            *[t.name for t in self.teachers],
            *[g.id for g in self.groups],
        ]
        return tuple(key)

    @property
    def id(self):
        return str(self._id)
