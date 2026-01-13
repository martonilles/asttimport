from pathlib import Path
from typing import Iterable, Any

from python_calamine import CalamineWorkbook, CalamineSheet

from asttimport.models import Classroom, ClassroomType, Teacher, Class, Assignment

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
        self.assignments = list(self._import_assignments(workbook.get_sheet_by_name("Beosztas")))

    def _import_classrooms(self, worksheet: CalamineSheet) -> Iterable[Classroom]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Classroom(name=row["Terem"], type=CLASSROMTYPE_MAPPING.get(row["Terem tipus"], ClassroomType.NORMAL))

    def _import_teachers(self, worksheet: CalamineSheet) -> Iterable[Teacher]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Teacher(name=row["Tanár"], email=row["Email"])

    def _import_class(self, worksheet: CalamineSheet) -> Iterable[Class]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Class(grade=row["Évfolyam"], name=row["Osztály"], classroom=self.classrooms[row["Terem"]], teachers=[
                self.teachers[teacher_name.strip()]
                for teacher_name in row["Tanár"].split(",")
            ])

    def _import_assignments(self, worksheet: CalamineSheet) -> Iterable[Assignment]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Assignment(grade=row["Évfolyam"],
                             subject=row["Tantárgy"],
                             class_=self.classes[row["Osztály"]] if row["Osztály"] not in ("", "Teljes") else None,
                             classroom_type=CLASSROMTYPE_MAPPING.get(row["Terem tipus"]) if row["Terem tipus"] not in ("", ) else None,
                             weekly_count=row["Óraszám"],
                             teachers=[
                                 self.teachers[teacher_name.strip()]
                                 for teacher_name in row["Tanár"].split(",")
                             ],
                             group=row["Csoport"] if row["Csoport"] not in ("", "Teljes") else None,
                             )

    @staticmethod
    def _convert_to_named_list(worksheet: CalamineSheet) -> list[dict[str, Any]]:
        data = worksheet.to_python(skip_empty_area=True)

        headers = data[0]
        rows = data[1:]

        return [dict(zip(headers, row)) for row in rows]
