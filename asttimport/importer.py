from typing import Iterable, Any

from python_calamine import CalamineWorkbook, CalamineSheet

from asttimport.models import (
    Classroom,
    Teacher,
    Class,
    Assignment,
    Subject,
    Group,
    MetaClass,
)
from asttimport.utils import parse_timeslots, info, error


class ExcelImporter:
    def __init__(self, base_data, assignment_excels_data):
        base_workbook = CalamineWorkbook.from_filelike(base_data)

        # Tantárgy

        self.classrooms = {
            classrom.name: classrom
            for classrom in self._import_classrooms(
                base_workbook.get_sheet_by_name("Terem")
            )
        }
        self.teachers = {
            teacher.name: teacher
            for teacher in self._import_teachers(
                base_workbook.get_sheet_by_name("Tanár")
            )
        }

        self.classes: dict[str, Class] = {}
        self.metaclasses: dict[str, MetaClass] = {}
        self.all_classes: dict[str, Class | MetaClass] = {}

        self._import_class(base_workbook.get_sheet_by_name("Osztály"))

        self.assignments: list[Assignment] = []
        self.subjects: dict[str, Subject] = {}
        self.groups: set[Group] = set()

        for name, data in assignment_excels_data.items():
            workbook = CalamineWorkbook.from_filelike(data)
            info(f"Importing {name}...")
            self.assignments.extend(
                self._import_assignments(workbook.get_sheet_by_name("Beosztás"))
            )

    def _import_classrooms(self, worksheet: CalamineSheet) -> Iterable[Classroom]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Classroom(
                name=row["Terem"],
                type=row["Terem tipus"],
                timeslots=parse_timeslots(row["Órapreferencia"]),
            )

    def _import_teachers(self, worksheet: CalamineSheet) -> Iterable[Teacher]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Teacher(
                name=row["Tanár"],
                email=row["Email"],
                timeslots=parse_timeslots(row["Órapreferencia"]),
            )

    def _import_class(self, worksheet: CalamineSheet) -> Iterable[Class]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            try:
                # classroom = self.classrooms[row["Terem"]] if row["Terem"] else None
                classroom = None
            except KeyError:
                error(f"Missing classroom: '{row['Terem']}' -> {row['Osztály Név']}")
                continue

            try:
                teachers = (
                    [
                        self.teachers[teacher_name.strip()]
                        for teacher_name in row["Tanár"].split(",")
                    ]
                    if row["Tanár"]
                    else []
                )
            except KeyError:
                error(f"Missing teacher: '{row['Tanár']}' -> {row['Osztály Név']}")
                continue

            name = row["Osztály"]
            ref_name = row["Osztály Név"]
            grade = int(row["Évfolyam"])

            if name in ("Alap", "Teljes"):
                class_names = (
                    [c.strip() for c in row["Osztályok"].split(",")]
                    if row["Osztályok"]
                    else []
                )
                class_ = MetaClass(
                    ref_name=ref_name, grade=grade, class_names=class_names, classes=[]
                )
                self.metaclasses[ref_name] = class_
            else:
                class_ = Class(
                    ref_name=ref_name,
                    grade=grade,
                    name=name,
                    classroom=classroom,
                    teachers=teachers,
                    timeslots=parse_timeslots(row["Órapreferencia"]),
                )
                self.classes[ref_name] = class_
            self.all_classes[ref_name] = class_

        for metaclass in self.metaclasses.values():
            if metaclass.class_names:
                metaclass.classes = [
                    self.classes[class_name] for class_name in metaclass.class_names
                ]
            else:
                metaclass.classes = [
                    class_
                    for class_ in self.classes.values()
                    if class_.grade == metaclass.grade
                ]

    def _import_assignments(self, worksheet: CalamineSheet) -> list[Assignment]:
        data = self._convert_to_named_list(worksheet)
        assignments: list[Assignment] = []
        for row in data:
            try:
                class_ = self.all_classes[row["Osztály"]]
            except KeyError:
                error(f"Missing class: '{row['Osztály']}' -> {row}")
                continue

            classes = [class_] if isinstance(class_, Class) else class_.classes

            group_name = (
                row["Csoport"] if row["Csoport"] not in ("", "Teljes") else None
            )
            if group_name:
                groups = [
                    Group(name=group_name, class_=other_class)
                    for other_class in classes
                ]
            else:
                groups = []

            self.groups.update(groups)

            subject = self.subjects.setdefault(
                row["Tantárgy"],
                Subject(
                    name=row["Tantárgy"],
                    timeslots=parse_timeslots(row["Órapreferencia"]),
                ),
            )

            try:
                teachers = (
                    [
                        self.teachers[teacher_name.strip()]
                        for teacher_name in row["Tanár"].split(",")
                    ]
                    if row["Tanár"]
                    else []
                )
            except KeyError as e:
                error(f"Missing teacher: '{e}' -> {row}")
                continue

            try:
                weekly_count = int(row["Óraszám"])
            except ValueError as e:
                error(f"Invalid weekly_count ({e}): '{row['Óraszám']}' -> {row}")
                continue

            try:
                assignments.append(
                    Assignment(
                        grade=class_.grade,
                        subject=subject,
                        class_=class_ if isinstance(class_, Class) else None,
                        classroom_type=row["Terem tipus"]
                        if row["Terem tipus"] not in ("",)
                        else None,
                        weekly_count=weekly_count,
                        teachers=teachers,
                        groups=groups,
                    )
                )
            except ValueError as e:
                error(f"{e} -> {row}")

        return assignments

    @staticmethod
    def _convert_to_named_list(worksheet: CalamineSheet) -> list[dict[str, Any]]:
        data = worksheet.to_python(skip_empty_area=True)

        headers = data[0]
        rows = data[1:]

        return [dict(zip(headers, row)) for row in rows if row[0]]
