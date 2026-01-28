import sys
from pathlib import Path

from asttimport.downloader import get_timetable_excel
from asttimport.exporter import Exporter
from asttimport.importer import ExcelImporter


def main():
    arg = Path(sys.argv[1])
    if arg.exists():
        importer = ExcelImporter(path=arg)
    else:
        excel_data = get_timetable_excel(sys.argv[1])
        importer = ExcelImporter(data=excel_data)

    print(
        f"{len(importer.teachers)=} {len(importer.classes)=} {len(importer.classrooms)=} {len(importer.assignments)=}"
    )

    exporter = Exporter(importer)
    exporter.write(Path(sys.argv[2]))
