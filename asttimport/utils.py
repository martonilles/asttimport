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


def info(*args):
    print("INF", *args)


def error(*args):
    print("\033[93mERR\033[0m", *args)


def parse_timeslots(data: str) -> dict[int, dict[int, str]]:
    return {}
    timeslots = defaultdict(lambda: defaultdict(lambda: "1"))

    for slot in data.split(","):
        slot = slot.strip()
        if not slot:
            continue

        day = DAYS.get(slot[0])
        if slot[1] in ("+", "-", "?"):
            for period in range(10):
                timeslots[day][period] = PREF_MAP.get(slot[1], "1")
        else:
            period = int(slot[1])
            pref = PREF_MAP.get(slot[2:], "1")

            timeslots[day][period] = pref

    return timeslots
