import csv
import os
import pickle
import sys
from pathlib import Path

from asttimport.downloader import get_timetable_excel, authenticate
from asttimport.exporter import Exporter
from asttimport.importer import ExcelImporter
from asttimport.utils import info, error

CACHE_DIR = Path(".cache")

BASE_EXCEL_ID = "1QSRwr0HdSRk-CpIeJF1OIyj0AgLZN9kh2n1U6eVQ3Ps"

ASSIGNMENT_EXCEL_IDS: dict[str, str] = {
    "angol": "1dcn3fsdvLSAlg42w0b9j5v_Oy53ldU7vngQdJ0mLIBM",
    "digi": "1j92m42sp8y99HWoMSjyb8zPeSXuuMTgSrNSJH_nRMt4",
    "egyeb": "1PZRtKAaYCQapgyvoeUsw6Fp1E9ImtdeUG6Us018seLk",
    # "elemi": "1EeyT3egM6kRdgrI-0SrypT2n5VcaQKWZ-3QsycOcPGw",
    "english": "1YivoXspWgrR0OiZuPmS7YeFZik2Mr3BE7o4Y-dx1Msk",
    "gazdasagi": "1ybs9EJ0ALiJHqtQpbZWtMJ-A-1R7ZnSqsoH7LBVhF-Y",
    "heber": "1yy2Pduwz4dmaDTp7Ya_cPGC1kTHOMz5jYP7lr-RVhp0",
    "nyelv": "1hEU4E5Fmt9Y34IEZ5FD2kNjbnJeytGLW2lL8vApr9ss",
    "judaisztika": "1qVxVd4wzytDr6KAMX35XY_Z8WTob6VE1fFVQruEZC-M",
    "magyar": "1bRv4hgdxRRgqTESIbVv5Ow_o0NoRU_5Uw16SLcacQGs",
    "matek": "1-diqrpqIDMYC3BQEfGcpiaax9UX8SeV9C9aWt81UuIQ",
    "science": "1v1jEwHx01jcUy9MlQ7br68FW8Ya4lN8m5rGPpOJsaxk",
    "testneveles": "1Pihs6LK42hWfPULMAAxo2BMXAdcYjQXYMzW1d9pxA-g",
    "tortenelem": "1CwvlIUBbfPBkRKnE4znMaqCkhMJ6Q9L6EIKQ81EjpcY",
    "vizu": "1Y7Hg_y58FoWYnaVSPorixGMeCaSyAeZ5BouzLKYWnZg",
}


def get_cache_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.pickle"


def load_cache(name):
    if (
        os.environ.get("USE_CACHE", 0) == "0"
        or os.environ.get("RENEW_CACHE", "") == name
    ):
        return None

    cache_path = get_cache_path(name)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        with cache_path.open("rb") as f:
            info(f"Loading cache {name}...")
            return pickle.load(f)
    return None


def save_cache(name: str, data):
    cache_path = get_cache_path(name)

    with cache_path.open("wb+") as f:
        pickle.dump(data, f)


def main():
    service = authenticate()

    base_excel_data = load_cache("base")
    if base_excel_data is None:
        base_excel_data = get_timetable_excel(service, "base", BASE_EXCEL_ID)
        save_cache("base", base_excel_data)

    assignment_excels_data = {}
    for name, excel_id in ASSIGNMENT_EXCEL_IDS.items():
        if sys.argv[1:] and name not in sys.argv[1:]:
            continue
        excel_data = load_cache(name)
        if excel_data is None:
            excel_data = get_timetable_excel(service, name, excel_id)
            save_cache(name, excel_data)
        assignment_excels_data[name] = excel_data

    importer = ExcelImporter(base_excel_data, assignment_excels_data)

    print(
        f"{len(importer.teachers)=} {len(importer.classes)=} {len(importer.classrooms)=} {len(importer.assignments)=}"
    )

    exporter = Exporter(importer)
    exporter.write(Path("orarend.xml"))

    with Path("orarend.csv").open("w+") as f:
        c = csv.writer(f, delimiter=";")
        c.writerow(
            [
                "Tanár",
                "Tantárgy",
                "Évfolyam",
                "Osztály",
                "Óraszám",
                "Időszak",
                "AN óra",
                "Csoport",
            ]
        )

        for assignment in importer.assignments:
            class_names = ",".join([c.name for c in assignment.classes])
            grades = {str(c.grade) for c in assignment.classes} | {
                str(g.class_.grade) for g in assignment.groups
            }
            for teacher in assignment.teachers:
                c.writerow(
                    [
                        teacher.name,
                        assignment.subject.name,
                        ",".join(grades),
                        class_names,
                        assignment.weekly_count,
                        assignment.term.name,
                        assignment.active_day_count,
                        ",".join({g.name for g in assignment.groups}),
                    ]
                )

    # groups_by_class = defaultdict(set)
    # for group in importer.groups:
    #     groups_by_class[group.class_].add(group)
    #
    # for class_, groups in sorted(groups_by_class.items(), key=lambda x: (x[0].grade, x[0].name)):
    #     group_bases = defaultdict(set)
    #     for group in groups:
    #         group_bases[group.base].add(group.name)
    #     print(class_.grade, class_.name)
    #     print(f" - Bases {len(group_bases)}:", ", ".join(sorted(group_bases.keys())))
    #     for base, groups in sorted(group_bases.items(), key=lambda x: x[0]):
    #         print(f"  - {base}: {len(groups)}:", ", ".join(sorted(groups)))
    #
    #
    assignments = {}
    for assignment in importer.assignments:
        if assignment.key in assignments:
            error(
                "DUPLICATE:", assignment.key
            )  # , assignment, assignments[assignment.key])
        else:
            assignments[assignment.key] = assignment
