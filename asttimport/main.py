import sys
from pathlib import Path

from asttimport.exporter import Exporter
from asttimport.importer import ExcelImporter


def main():
    importer = ExcelImporter(Path(sys.argv[1]))

    print(
        f"{len(importer.teachers)=} {len(importer.classes)=} {len(importer.classrooms)=} {len(importer.assignments)=}"
    )

    exporter = Exporter(importer)
    exporter.write(Path(sys.argv[2]))
