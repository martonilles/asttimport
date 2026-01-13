from pathlib import Path

from pydantic_xml import BaseXmlModel, attr, RootXmlModel, element

from asttimport.importer import ExcelImporter
from asttimport.utils import clean_id


class Teacher(BaseXmlModel, tag="teacher"):
    id: str = attr("id")
    name: str = attr("name")
    short: str = attr("short")
    email: str = attr("email")


class Teachers(BaseXmlModel, tag="teachers"):
    options: str = attr("options", default="")
    columns: str = attr("columns", default="id,name,short,email")
    teachers: list[Teacher]

class Class(BaseXmlModel, tag="class"):
    id: str = attr("id")
    name: str = attr("name")
    short: str = attr("short")
    grade: int = attr("grade")
    classroomids: str = attr("classroomids", default="", )

class Classes(BaseXmlModel, tag="classes"):
    options: str = attr("options", default="")
    columns: str = attr("columns", default="id,name,short,grade,classroomids")
    classes: list[Class]

class ClassRoom(BaseXmlModel, tag="classroom"):
    id: str = attr("id")
    name: str = attr("name")
    short: str = attr("short")


class ClassRooms(BaseXmlModel, tag="classrooms"):
    options: str = attr("options", default="")
    columns: str = attr("columns", default="id,name,short")
    classrooms: list[ClassRoom]


class Subject(BaseXmlModel, tag="subject", frozen=True):
    id: str = attr("id")
    name: str = attr("name")
    short: str = attr("short")

class Subjects(BaseXmlModel, tag="subjects"):
    options: str = attr("options", default="")
    columns: str = attr("columns", default="id,name,short")
    subjects: set[Subject]


class Group(BaseXmlModel, tag="group", frozen=True):
    id: str = attr("id")
    name: str = attr("name")
    classid: str = attr("classid")
    entireclass: str = attr("entireclass")
    divisiontag: str = attr("divisiontag")

class Groups(BaseXmlModel, tag="groups"):
    options: str = attr("options", default="")
    columns: str = attr("columns", default="id,name,classid,entireclass,divisiontag")
    groups: set[Group]

class Lesson(BaseXmlModel, tag="lesson", frozen=True):
    id: str = attr("id")
    subjectid: str = attr("subjectid")
    groupids: str = attr("groupids")
    classids: str = attr("classids")
    teacherids: str = attr("teacherids")
    classroomids: str = attr("classroomids")
    durationperiods: int = attr("durationperiods")
    periodsperweek: float = attr("periodsperweek")

class Lessons(BaseXmlModel, tag="lessons"):
    options: str = attr("options", default="")
    columns: str = attr("columns", default="id,subjectid,groupids,classids,teacherids,classroomids,durationperiods,periodsperweek")
    lessons: set[Lesson]

class Timetable(BaseXmlModel, tag='timetable'):
    importtype: str = attr(default="database")
    options: str = attr(default="idprefix:MyApp")

    teachers: Teachers
    classrooms: ClassRooms
    classes: Classes
    subjects: Subjects
    groups: Groups
    lessons: Lessons


class Exporter:
    def __init__(self, importer: ExcelImporter):
        self.teachers = importer.teachers
        self.classes = importer.classes
        self.classrooms = importer.classrooms
        self.assignments = importer.assignments

    def build(self):
        teachers = Teachers(teachers=[
            Teacher(id=teacher.id, name=teacher.name, email=teacher.email, short=teacher.username)
            for teacher in self.teachers.values()
        ])

        classrooms = ClassRooms(classrooms=[
            ClassRoom(id=classroom.id, name=classroom.name, short=classroom.name)
            for classroom in self.classrooms.values()
        ])

        classes = Classes(classes=[
            Class(id=class_.id, name=f"{int(class_.grade)}. {class_.name}", short=class_.name, grade=class_.grade, classroomids=class_.classroom.id)
            for class_ in self.classes.values()
        ])

        subjects = Subjects(subjects={
            Subject(id=clean_id(f"S_{assignment.subject}"), name=assignment.subject, short=assignment.subject)
            for assignment in self.assignments
        })

        groups = {
                        Group(id=clean_id(f"G_{int(assignment.grade)}_{assignment.class_.name}_{assignment.group}"),
                              name=assignment.group,
                              classid=assignment.class_.id,
                              divisiontag=assignment.group.split("/")[0],
                              entireclass="0",)
                        for assignment in self.assignments
                        if assignment.group is not None and assignment.class_ is not None
        } | {
            Group(id=clean_id(f"G_{int(assignment.grade)}_{assignment.class_.name}_Teljes"),
                  name="Teljes",
                  classid=assignment.class_.id,
                  divisiontag="",
                  entireclass="1", )
            for assignment in self.assignments
            if assignment.group is None and assignment.class_ is not None
        } | {
            Group(id=clean_id(f"G_{int(assignment.grade)}_{class_.name}_{assignment.group}"),
                  name=assignment.group,
                  classid=class_.id,
                  divisiontag=assignment.group.split("/")[0],
                  entireclass="0", )
            for assignment in self.assignments
            if assignment.group is not None and assignment.class_ is None
            for class_ in self.classes.values()
            if class_.grade == assignment.grade
        }

        lessons = {
            Lesson(
                id=clean_id(f"L_{assignment.class_.id}_{assignment.subject}"),
                subjectid=clean_id(f"S_{assignment.subject}"),
                classids=assignment.class_.id,
                groupids="",
                teacherids=",".join([teacher.id for teacher in assignment.teachers]),
                classroomids="",
                durationperiods=1,
                periodsperweek=assignment.weekly_count
            )
            for assignment in self.assignments
            if assignment.class_ is not None and assignment.group is None
        } | {
            Lesson(
                id=clean_id(f"L_{assignment.class_.id}_{assignment.subject}_{assignment.group}"),
                subjectid=clean_id(f"S_{assignment.subject}"),
                classids=assignment.class_.id,
                groupids=clean_id(f"G_{int(assignment.grade)}_{assignment.class_.name}_{assignment.group}"),
                teacherids=",".join([teacher.id for teacher in assignment.teachers]),
                classroomids="",
                durationperiods=1,
                periodsperweek=assignment.weekly_count
            )
            for assignment in self.assignments
            if assignment.class_ is not None and assignment.group is not None
        }

        timetable = Timetable(
            teachers=teachers,
            classrooms=classrooms,
            classes=classes,
            subjects=subjects,
            groups=Groups(groups=groups),
            lessons=Lessons(lessons=lessons),
        )

        return timetable

    def write(self, path: Path):
        timetable = self.build()
        xml  = timetable.to_xml(
            pretty_print=True,
            encoding='UTF-8',
            standalone=True,
            xml_declaration=True,
)

        path.write_bytes(xml)
