from typing import Iterable, Any
from unittest import case

from python_calamine import CalamineWorkbook, CalamineSheet

from asttimport.models import (
    Classroom,
    Teacher,
    Class,
    Assignment,
    Subject,
    Group,
    MetaClass, Term,
)
from asttimport.utils import parse_timeslots, info, error, warning


class ExcelImporter:
    def __init__(self, base_data, assignment_excels_data):
        base_workbook = CalamineWorkbook.from_filelike(base_data)

        self.subjects = {
            subject.name: subject
            for subject in self._import_subjects(base_workbook.get_sheet_by_name("Tantárgy"))
        }

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
        self.groups: set[Group] = set()

        for name, data in assignment_excels_data.items():
            workbook = CalamineWorkbook.from_filelike(data)
            info(f"Importing {name}...")
            self.assignments.extend(
                self._import_assignments(workbook.get_sheet_by_name("Beosztás"))
            )

    def _import_subjects(self, worksheet: CalamineSheet) -> Iterable[Subject]:
        data = self._convert_to_named_list(worksheet)
        for row in data:
            yield Subject(
                name=row["Tantárgy"],
                timeslots=parse_timeslots(row["Órapreferencia"]),
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
            if row.get("Import"):
                warning(f"Skip importing assignment '{row['Import']}': '{row}'")
                continue

            try:
                class_names = {
                    class_name.strip()
                    for class_name in row["Osztály"].strip().split(",")
                    if class_name.strip()
                }

                classes: list[Class] = []
                for class_name in class_names:
                    class_ = self.all_classes[class_name]
                    classes.extend([class_] if isinstance(class_, Class) else class_.classes)
            except KeyError:
                error(f"Missing class: '{row['Osztály']}' -> {row}")
                continue

            group_names = [
                group_name.strip()
                for group_name in row["Csoport"].split(",")
                if group_name.strip()
            ]

            groups = []
            for group_name in group_names:
                assert isinstance(group_name, str), row
                assert "/" in group_name, row
                groups.extend([
                    Group(name=group_name, class_=other_class)
                    for other_class in classes
                ])

            self.groups.update(groups)

            try:
                subject = self.subjects[row["Tantárgy"]]
            except KeyError as e:
                error(f"Missing subject: '{e}' -> {row}")
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
            except KeyError as e:
                error(f"Missing teacher: '{e}' -> {row}")
                continue

            try:
                weekly_count = int(row["Óraszám"])
            except ValueError as e:
                error(f"Invalid weekly_count ({e}): '{row['Óraszám']}' -> {row}")
                continue

            double_count = int(row["Dupla óra"]) if row.get("Dupla óra") else 0
            active_day_count = int(row["AN óra"]) if row.get("AN óra") else 0
            room_count = int(row["Terem darab"]) if row.get("Terem darab") else 1
            term = self._get_term(row.get("Időszak", ""))

            try:
                assignments.append(
                    Assignment(
                        subject=subject,
                        classes=classes,
                        classroom_type=row["Terem tipus"]
                        if row["Terem tipus"] not in ("",)
                        else None,
                        weekly_count=weekly_count,
                        teachers=teachers,
                        groups=groups,
                        term=term,
                        double_count=double_count,
                        active_day_count=active_day_count,
                        classroom_count=room_count,
                    )
                )
            except ValueError as e:
                error(f"{e} -> {row}")

        return assignments

    @staticmethod
    def _get_term(term) -> Term:
        match term:
            case 1:
                return Term.FIRST
            case 2:
                return Term.SECOND
            case _:
                return Term.FULL

    @staticmethod
    def _convert_to_named_list(worksheet: CalamineSheet) -> list[dict[str, Any]]:
        data = worksheet.to_python(skip_empty_area=True)

        headers = data[0]
        rows = data[1:]

        return [dict(zip(headers, row)) for row in rows if row[0]]
