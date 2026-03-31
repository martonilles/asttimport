import dataclasses
import uuid
from enum import Enum

from asttimport.utils import clean_id


TIMESLOTS = dict[int, dict[int, str]]


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
        assert isinstance(self.name, str), self
        return self.name.split("/")[0]

    @property
    def id(self):
        return clean_id(f"G_{self.class_.grade}_{self.class_.name}_{self.name}")

    def __hash__(self):
        return hash(self.id)


@dataclasses.dataclass
class Assignment:
    subject: Subject
    teachers: list[Teacher]
    classroom_type: str | None
    grade: int
    class_: Class | None
    groups: list[Group]
    weekly_count: int

    def __post_init__(self):
        if self.class_ is None and not self.groups:
            raise ValueError(
                f"Assignment must have at least one group when class is not set: {self}"
            )

    @property
    def id(self):
        return str(uuid.uuid4())
        if self.class_ is not None:
            base = f"A_{int(self.class_.grade)}_{self.class_.name}_{self.subject.name}"
        else:
            base = f"A_{int(self.grade)}_TELJES_{self.subject.name}"

        if self.groups:
            group_names = "-".join({group.name for group in self.groups})
            return clean_id(f"{base}_{group_names}")

        return clean_id(base)
