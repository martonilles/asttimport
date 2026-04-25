from pathlib import Path

from pydantic_xml import BaseXmlModel, attr

from asttimport.importer import ExcelImporter
from asttimport.models import Term
from asttimport.utils import NUM_PERIODS


class Teacher(BaseXmlModel, tag="teacher"):
    id: str = attr("id")
    name: str = attr("name")
    short: str = attr("short")
    email: str = attr("email")
    timeoff: str = attr("timeoff")


class Teachers(BaseXmlModel, tag="teachers"):
    options: str = attr("options", default="")
    columns: str = attr("columns", default="id,name,short,email,timeoff")
    teachers: list[Teacher]


class Class(BaseXmlModel, tag="class"):
    id: str = attr("id")
    name: str = attr("name")
    short: str = attr("short")
    grade: int = attr("grade")
    classroomids: str = attr(
        "classroomids",
        default="",
    )


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
    timeoff: str = attr("timeoff")


class Subjects(BaseXmlModel, tag="subjects"):
    options: str = attr("options", default="")
    columns: str = attr("columns", default="id,name,short,timeoff")
    subjects: list[Subject]


class Group(BaseXmlModel, tag="group", frozen=True):
    id: str = attr("id")
    name: str = attr("name")
    classid: str = attr("classid")
    entireclass: str = attr("entireclass")
    divisiontag: str = attr("divisiontag")


class Groups(BaseXmlModel, tag="groups"):
    options: str = attr("options", default="primarydb")
    columns: str = attr("columns", default="id,name,classid,entireclass,divisiontag")
    groups: list[Group]


class Lesson(BaseXmlModel, tag="lesson", frozen=True):
    id: str = attr("id")
    subjectid: str = attr("subjectid")
    groupids: str = attr("groupids")
    classids: str = attr("classids")
    teacherids: str = attr("teacherids")
    classroomids: str = attr("classroomids")
    durationperiods: int = attr("durationperiods", default=1)
    periodsperweek: float = attr("periodsperweek")
    termsdefid: str = attr("termsdefid")
    daysdefid: str = attr("daysdefid")


class Lessons(BaseXmlModel, tag="lessons"):
    options: str = attr("options", default="primarydb")
    columns: str = attr(
        "columns",
        default="id,subjectid,groupids,classids,teacherids,classroomids,durationperiods,periodsperweek,termsdefid,daysdefid",
    )
    lessons: list[Lesson]


class TermsDefinition(BaseXmlModel, tag="termsdef", frozen=True):
    id: str = attr("id")
    terms: str = attr("terms")
    name: str = attr("name")
    short: str = attr("short")


class TermsDefinitions(BaseXmlModel, tag="termsdefs", frozen=True):
    options: str = attr("options", default="primarydb")
    columns: str = attr(
        "columns",
        default="id,terms,name,short",
    )
    definitions: list[TermsDefinition]


class DaysDefinition(BaseXmlModel, tag="daysdef", frozen=True):
    id: str = attr("id")
    days: str = attr("days")
    name: str = attr("name")
    short: str = attr("short")


class DaysDefinitions(BaseXmlModel, tag="daysdefs", frozen=True):
    options: str = attr("options", default="primarydb")
    columns: str = attr(
        "columns",
        default="id,days,name,short",
    )
    definitions: list[DaysDefinition]


class Period(BaseXmlModel, tag="period", frozen=True):
    period: str = attr("period")
    name: str = attr("name")
    short: str = attr("short")


class Periods(BaseXmlModel, tag="periods", frozen=True):
    options: str = attr("options", default="primarydb")
    columns: str = attr(
        "columns",
        default="period,name,short",
    )
    definitions: list[Period]


class Timetable(BaseXmlModel, tag="timetable"):
    importtype: str = attr(default="database")
    options: str = attr(default="idprefix:MyApp")

    periods: Periods
    terms_definitions: TermsDefinitions
    days_definitions: DaysDefinitions
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
        self.subjects = importer.subjects.values()
        self.groups = importer.groups
        self.assignments = importer.assignments

    def build(self):
        periods = [
            Period(period=str(period), name=str(period), short=str(period))
            for period in range(1, NUM_PERIODS)
        ]

        full_year = TermsDefinition(
            id="TERM_FULL", terms="11", name="Egész év", short="YR"
        )
        first_term = TermsDefinition(
            id="TERM_FIRST", terms="10", name="Első félév", short="F1"
        )
        second_term = TermsDefinition(
            id="TERM_SECOND", terms="01", name="Második félév", short="F2"
        )
        terms_definitions = [full_year, first_term, second_term]
        terms_mapping = {
            Term.FIRST: first_term,
            Term.SECOND: second_term,
            Term.FULL: full_year,
        }

        days_definitions = [
            DaysDefinition(
                id="D_X",
                days="10000,01000,00100,00010,00001",
                name="Bármely nap",
                short="X",
            ),
            DaysDefinition(id="D_H", days="10000", name="Hétfő", short="H"),
            DaysDefinition(id="D_K", days="01000", name="Kedd", short="K"),
            DaysDefinition(id="D_S", days="00100", name="Szerda", short="S"),
            DaysDefinition(id="D_C", days="00010", name="Csütörtök", short="C"),
            DaysDefinition(id="D_P", days="00001", name="Péntek", short="P"),
            # DaysDefinition(id="D_10N", days="10000,00100,00010,00001", name="10. normál nap", short="10-N"),
            DaysDefinition(
                id="D_11N",
                days="10000,01000,00010,00001",
                name="11. normál nap",
                short="11-N",
            ),
            DaysDefinition(
                id="D_12N",
                days="10000,01000,00100,00001",
                name="12. normál nap",
                short="12-N",
            ),
        ]

        normal_day_mapping = {
            # 10: "D_10N",
            11: "D_11N",
            12: "D_12N",
        }

        active_day_mapping = {
            # 10: "D_K",
            11: "D_S",
            12: "D_C",
        }

        teachers = [
            Teacher(
                id=teacher.id,
                name=teacher.name,
                email=teacher.email,
                short=teacher.username,
                timeoff=teacher.timeoff,
            )
            for teacher in self.teachers.values()
        ]

        classrooms = [
            ClassRoom(id=classroom.id, name=classroom.name, short=classroom.name)
            for classroom in self.classrooms.values()
        ]

        classes = [
            Class(
                id=class_.id,
                name=f"{int(class_.grade)}. {class_.name}",
                short=class_.name,
                grade=class_.grade,
                classroomids=class_.classroom.id
                if class_.classroom is not None
                else "",
            )
            for class_ in self.classes.values()
        ]

        subjects = [
            Subject(
                id=subject.id,
                name=subject.name,
                short=subject.name,
                timeoff=subject.timeoff,
            )
            for subject in self.subjects
        ]

        groups = [
            Group(
                id=group.id,
                name=group.name,
                classid=group.class_.id,
                divisiontag=group.base,
                entireclass="0",
            )
            for group in sorted(
                self.groups, key=lambda group: (group.class_.id, group.name)
            )
        ]

        lessons = []
        for assignment in self.assignments:
            term_divider = 1 if assignment.term is Term.FULL else 2
            normal_day_def = normal_day_mapping.get(assignment.classes[0].grade, "X") if assignment.classes else "X"

            if assignment.double_count or assignment.active_day_count:
                normal_count = (
                    assignment.weekly_count
                    - (assignment.double_count * 2)
                    - assignment.active_day_count
                )
                if normal_count:
                    lessons.append(
                        Lesson(
                            id=f"{assignment.id}-normal",
                            subjectid=assignment.subject.id,
                            classids=",".join(
                                [class_.id for class_ in assignment.classes]
                            )
                            if assignment.classes
                            else ",".join(
                                [group.class_.id for group in assignment.groups]
                            ),
                            groupids=",".join(
                                [group.id for group in assignment.groups]
                            ),
                            teacherids=",".join(
                                [teacher.id for teacher in assignment.teachers]
                            ),
                            classroomids="",
                            durationperiods=1,
                            periodsperweek=normal_count / term_divider,
                            termsdefid=terms_mapping[assignment.term].id,
                            daysdefid=normal_day_def,
                        )
                    )
                if assignment.active_day_count and False:
                    lessons.append(
                        Lesson(
                            id=f"{assignment.id}-active",
                            subjectid=assignment.subject.id,
                            classids=",".join(
                                [class_.id for class_ in assignment.classes]
                            )
                            if assignment.classes
                            else ",".join(
                                [group.class_.id for group in assignment.groups]
                            ),
                            groupids=",".join(
                                [group.id for group in assignment.groups]
                            ),
                            teacherids=",".join(
                                [teacher.id for teacher in assignment.teachers]
                            ),
                            classroomids="",
                            durationperiods=assignment.active_day_count,
                            periodsperweek=assignment.active_day_count / term_divider,
                            termsdefid=terms_mapping[assignment.term].id,
                            daysdefid=active_day_mapping[assignment.classes[0].grade],
                        )
                    )
                if assignment.double_count:
                    lessons.append(
                        Lesson(
                            id=f"{assignment.id}-double",
                            subjectid=assignment.subject.id,
                            classids=",".join(
                                [class_.id for class_ in assignment.classes]
                            )
                            if assignment.classes
                            else ",".join(
                                [group.class_.id for group in assignment.groups]
                            ),
                            groupids=",".join(
                                [group.id for group in assignment.groups]
                            ),
                            teacherids=",".join(
                                [teacher.id for teacher in assignment.teachers]
                            ),
                            classroomids="",
                            durationperiods=2,
                            periodsperweek=assignment.double_count * 2 / term_divider,
                            termsdefid=terms_mapping[assignment.term].id,
                            daysdefid=normal_day_def,
                        )
                    )
            else:
                lessons.append(
                    Lesson(
                        id=assignment.id,
                        subjectid=assignment.subject.id,
                        classids=",".join([class_.id for class_ in assignment.classes])
                        if assignment.classes
                        else ",".join([group.class_.id for group in assignment.groups]),
                        groupids=",".join([group.id for group in assignment.groups]),
                        teacherids=",".join(
                            [teacher.id for teacher in assignment.teachers]
                        ),
                        classroomids="",
                        durationperiods=1,
                        periodsperweek=assignment.weekly_count / term_divider,
                        termsdefid=terms_mapping[assignment.term].id,
                        daysdefid=normal_day_def,
                    )
                )

        timetable = Timetable(
            periods=Periods(definitions=periods),
            days_definitions=DaysDefinitions(definitions=days_definitions),
            terms_definitions=TermsDefinitions(definitions=terms_definitions),
            teachers=Teachers(teachers=teachers),
            classrooms=ClassRooms(classrooms=classrooms),
            classes=Classes(classes=classes),
            subjects=Subjects(subjects=subjects),
            groups=Groups(groups=groups),
            lessons=Lessons(lessons=lessons),
        )

        return timetable

    def write(self, path: Path):
        timetable = self.build()
        xml = timetable.to_xml(
            pretty_print=True,
            encoding="UTF-8",
            standalone=True,
            xml_declaration=True,
        )

        path.write_bytes(xml)
