from collections import defaultdict
from typing import Iterable, Any
import datetime as dt

from python_calamine import CalamineWorkbook, CalamineSheet

from asttimport.models import (
    Classroom,
    Teacher,
    Class,
    Assignment,
    Subject,
    Group,
    MetaClass,
    Term,
)
from asttimport.utils import parse_timeslots, info, error, warning, FACT_TIMESLOTS


class ExcelImporter:
    def __init__(self, base_data, assignment_excels_data):
        base_workbook = CalamineWorkbook.from_filelike(base_data)

        self.subjects = {
            subject.name: subject
            for subject in self._import_subjects(
                base_workbook.get_sheet_by_name("Tantárgy")
            )
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

        self._remap_assignment_subjects()

    def _remap_assignment_subjects(self):
        subject_timeslots_assignments = defaultdict(lambda: defaultdict(list))

        for assignment in self.assignments:
            subject_timeslots_assignments[assignment.subject][
                assignment.timeslots
            ].append(assignment)

        for subject, timeslots in subject_timeslots_assignments.items():
            if len(timeslots) > 1:
                info(f"Multiple timeslots: {subject.name} -> {timeslots.keys()}")

                timeslot_grades = {
                    timeslot: {c.grade for a in assignments for c in a.classes}
                    for timeslot, assignments in timeslots.items()
                }

                timeslot_classes = {
                    timeslot: {c.name for a in assignments for c in a.classes}
                    for timeslot, assignments in timeslots.items()
                }

                grades_are_disjoints = sum(map(len, timeslot_grades.values())) == len(
                    set().union(*timeslot_grades.values())
                )
                classes_are_disjoints = sum(map(len, timeslot_classes.values())) == len(
                    set().union(*timeslot_classes.values())
                )

                timeslot_mapping = None
                if all(not classes for classes in timeslot_classes.values()):
                    timeslot_mapping = {
                        timeslot: {idx}
                        for idx, timeslot in enumerate(timeslots.keys())
                    }
                elif grades_are_disjoints:
                    timeslot_mapping = timeslot_grades
                elif classes_are_disjoints:
                    timeslot_mapping = timeslot_classes

                if timeslot_mapping is not None:
                    info("- Mutating subjects")
                    for timeslot, assignments in timeslots.items():
                        if timeslot == subject.timeslots:
                            info(
                                f"  - Keeping timeslot as same as subject {timeslot} {timeslot_mapping[timeslot]}"
                            )
                        else:
                            new_name = f"{subject.name} ({','.join(sorted([str(key) for key in timeslot_mapping[timeslot]]))})"
                            info(
                                f"  - Creating new subject '{new_name}' {timeslot_mapping[timeslot]}"
                            )
                            new_subject = Subject(name=new_name, timeslots=timeslot)
                            self.subjects[new_subject.name] = new_subject
                            for assignment in assignments:
                                info("   - Assigning to lesson", assignment.key)
                                assignment.subject = new_subject

                else:
                    error("- Sets are not disjoints", timeslot_grades, timeslot_classes)
            elif (
                subject.timeslots != list(timeslots)[0]
                and subject.timeslots is not None
                and list(timeslots)[0] is not None
            ):
                error(f"Conflicting timeslots: {subject.name} -> {timeslots.keys()}")
                # print(" * ", subject.timeslots)
                # for timeslot, assignments in timeslots.items():
                #     print(" - ", timeslot, {c.grade for a in assignments for c in a.classes}, {c.name for a in assignments for c in a.classes})
            elif (
                subject.timeslots != list(timeslots)[0]
                and subject.timeslots is not None
            ):
                info(
                    f"Inheriting timeslots, nothing to do: {subject.name} -> {timeslots.keys()}"
                )
                # print(" * ", subject.timeslots)
                # for timeslot, assignments in timeslots.items():
                #     print(" - ", timeslot, {c.grade for a in assignments for c in a.classes}, {c.name for a in assignments for c in a.classes})
            elif subject.timeslots != list(timeslots)[0] and subject.timeslots is None:
                info(f"Setting timeslots: {subject.name} -> {timeslots.keys()}")
                subject.timeslots = list(timeslots)[0]

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
                classrooms = [
                    self.classrooms[classroom.strip()]
                    for classroom in row["Terem"].strip().split(",")
                    if classroom.strip()
                ]
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
                    classrooms=classrooms,
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
                    classes.extend(
                        [class_] if isinstance(class_, Class) else class_.classes
                    )
            except KeyError:
                error(f"Missing class: '{row['Osztály']}' -> {row}")
                continue

            group_names = [
                group_name.strip()
                for group_name in row["Csoport"].split(",")
                if group_name.strip()
            ]

            fact = any(group_name.startswith("fakt") for group_name in group_names)

            groups = []
            for group_name in group_names:
                assert isinstance(group_name, str), row
                assert "/" in group_name, row
                groups.extend(
                    [
                        Group(name=group_name, class_=other_class)
                        for other_class in classes
                    ]
                )

            self.groups.update(groups)

            try:
                subject = self.subjects[row["Tantárgy"]]
            except KeyError as e:
                error(f"Missing subject: '{e}' -> {row}")
                continue

            if fact:
                subject = Subject(
                    name=f"{subject.name} - fakt", timeslots=FACT_TIMESLOTS
                )
                self.subjects[subject.name] = subject

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

            classroom_type = row["Terem tipus"].strip()
            if classroom_type:
                classrooms = [
                    classroom
                    for classroom in self.classrooms.values()
                    if classroom.type == classroom_type
                ]
                if not classrooms:
                    error(f"Invalid classroom type: '{classroom_type}' -> {row}")
            else:
                classrooms = [
                    classroom
                    for class_ in classes
                    for classroom in class_.classrooms
                ]
            classrooms = []

            double_count = int(row["Dupla óra"]) if row.get("Dupla óra") else 0
            active_day_count = int(row["AN óra"]) if row.get("AN óra") else 0
            room_count = int(row["Terem darab"]) if row.get("Terem darab") else 1
            term = self._get_term(row.get("Időszak", ""))

            timeslot_data = row["Órapreferencia"]
            if isinstance(timeslot_data, float):
                timeslot_data = str(int(timeslot_data))
            elif isinstance(timeslot_data, int):
                timeslot_data = str(timeslot_data)
            elif isinstance(timeslot_data, dt.datetime):
                timeslot_data = str(timeslot_data)
            elif isinstance(timeslot_data, dt.date):
                timeslot_data = str(timeslot_data)

            try:
                assignments.append(
                    Assignment(
                        subject=subject,
                        classes=classes,
                        classrooms=classrooms,
                        weekly_count=weekly_count,
                        timeslots=parse_timeslots(timeslot_data, str(row)),
                        fact=fact,
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
