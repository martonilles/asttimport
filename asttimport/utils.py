from collections import defaultdict


def clean_id(base: str) -> str:
    return base.replace(".", "-").replace(" ", "-").replace("/", "-")


DAYS = {
    "H": 0,
    "K": 1,
    "S": 2,
    "C": 3,
    "P": 4,
}

PREF_MAP = {
    "+": "1",
    "?": "?",
    "-": "0",
}


def parse_timeslots(data: str) -> dict[int, dict[int, str]]:
    timeslots = defaultdict(lambda: defaultdict(lambda: "1"))

    for slot in data.split(","):
        if not slot:
            continue

        day = DAYS.get(slot[0])
        period = int(slot[1])
        pref = PREF_MAP.get(slot[2:], "1")

        timeslots[day][period] = pref

    return timeslots
