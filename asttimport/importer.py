from pathlib import Path
from typing import Iterable, Any

from python_calamine import CalamineWorkbook, CalamineSheet

from asttimport.models import Classroom, ClassroomType, Teacher, Class, Assignment, Subject, Group
from asttimport.utils import parse_timeslots

CLASSROMTYPE_MAPPING = {
    "INFO": ClassroomType.INFO,
    "TORNA": ClassroomType.GYM,
    "AVK": ClassroomType.MEDIA,
    "SPEC": ClassroomType.SPECIAL,
    "FEJLESZTO": ClassroomType.DEVELOPMENT,
    "TANARI": ClassroomType.TEACHER,
    "BIO": ClassroomType.LAB,
    "KICSI": ClassroomType.SMALL,
    "TARGYALO": ClassroomType.MEETING,
}


class ExcelImporter:
    def __init__(self, path: Path):
        self.path = path

        workbook = CalamineWorkbook.from_path(path)

        self.classrooms = {
            classrom.name: classrom
            for classrom in self._import_classrooms(workbook.get_sheet_by_name("Terem"))
            }
        self.teachers = {
            teacher.name: teacher
            for teacher in self._import_teachers(workbook.get_sheet_by_name("Tanar"))
            }
        self.classes = {
            class_.name:class_
            for class_ in self._import_class(workbook.get_sheet_by_name("Osztaly"))
        }
        self.assignments, self.subjects, self.groups = self._import_assignments(workbook.get_sheet_by_name("Beosztas"))

    def _import_classrooms(self, worksheet: CalamineSheet) -> Iterable[Classroom]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Classroom(name=row["Terem"], type=CLASSROMTYPE_MAPPING.get(row["Terem tipus"], ClassroomType.NORMAL), timeslots=parse_timeslots(row["Órapreferencia"]))

    def _import_teachers(self, worksheet: CalamineSheet) -> Iterable[Teacher]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Teacher(name=row["Tanár"], email=row["Email"], timeslots=parse_timeslots(row["Órapreferencia"]))

    def _import_class(self, worksheet: CalamineSheet) -> Iterable[Class]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Class(grade=row["Évfolyam"], name=row["Osztály"], classroom=self.classrooms[row["Terem"]], teachers=[
                self.teachers[teacher_name.strip()]
                for teacher_name in row["Tanár"].split(",")
            ], timeslots=parse_timeslots(row["Órapreferencia"]))

    def _import_assignments(self, worksheet: CalamineSheet) -> tuple[list[Assignment], list[Subject], list[Group]]:
        data = self._convert_to_named_list(worksheet)
        assignments: list[Assignment] = []
        subjects: dict[str, Subject] = {}
        all_groups: set[Group] = set()
        for row in data:
            grade = row["Évfolyam"]
            class_ = self.classes[row["Osztály"]] if row["Osztály"] not in ("", "Teljes") else None
            group_name = row["Csoport"] if row["Csoport"] not in ("", "Teljes") else None
            if group_name:
                if class_ is not None:
                    groups = [Group(name=group_name, class_=class_),]
                else:
                    groups = [
                        Group(name=group_name, class_=other_class)
                        for other_class in self.classes.values()
                        if other_class.grade == grade
                    ]
            else:
                groups = []

            all_groups.update(groups)

            subject = subjects.setdefault(row["Tantárgy"], Subject(name=row["Tantárgy"], timeslots=parse_timeslots(row["Órapreferencia"])))
            assignments.append(Assignment(grade=grade,
                             subject=subject,
                             class_=class_,
                             classroom_type=CLASSROMTYPE_MAPPING.get(row["Terem tipus"]) if row["Terem tipus"] not in ("", ) else None,
                             weekly_count=row["Óraszám"],
                             teachers=[
                                 self.teachers[teacher_name.strip()]
                                 for teacher_name in row["Tanár"].split(",")
                             ],
                             groups=groups,
                             ))

        return assignments, list(subjects.values()), list(all_groups)

    @staticmethod
    def _convert_to_named_list(worksheet: CalamineSheet) -> list[dict[str, Any]]:
        data = worksheet.to_python(skip_empty_area=True)

        headers = data[0]
        rows = data[1:]

        return [dict(zip(headers, row)) for row in rows]
