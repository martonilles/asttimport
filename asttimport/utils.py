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

NUM_PERIODS = 10


def info(*args):
    print("INF", *args)

def warning(*args):
    print("\033[93mWAR\033[0m", *args)

def error(*args):
    print("\033[91mERR\033[0m", *args)


def get_timeoff(data: dict[int, dict[int, str]], default) -> str:
    daya_datas = []
    for day in DAYS.values():
        day_data = ""
        for period in range(NUM_PERIODS):
            v = data[day][period]
            if period == 0:
                v = "."
            day_data += v if v != "X" else default
        daya_datas.append(day_data)

    return ",".join(daya_datas)


def parse_timeslots(data: str) -> str:
    # info(f"Parsing timeslot '{data}'")
    timeslots = defaultdict(lambda: defaultdict(lambda: "X"))
    prefs = set()

    def update(day: int | None, period: int | None, value: str):
        prefs.add(value)
        if day is not None:
            if period is not None:
                timeslots[day][period] = value
            else:
                for p in range(NUM_PERIODS):
                    timeslots[day][p] = value
        else:
            for d in DAYS.values():
                timeslots[d][period] = value

    for slot in data.split(","):
        slot = slot.strip()
        if not slot:
            continue

        if slot[0] in DAYS:
            day = DAYS.get(slot[0])
            if slot[1] in ("+", "-", "?"):
                update(day=day, period=None, value=PREF_MAP.get(slot[1], "1"))
            else:
                update(day=day, period=int(slot[1]), value=PREF_MAP.get(slot[2:], "1"))
        elif slot[0].isnumeric():
            update(day=None, period=int(slot[0]), value=PREF_MAP.get(slot[1:], "1"))

    if prefs.intersection({"1", "0"}) == {"1", "0"}:
        error(f"Invalid timeslot '{data}'")

    default = "0" if "1" in prefs else "1"

    timeoff = get_timeoff(timeslots, default)

    # info(f"Parsed timeslots {timeoff}")
    return timeoff
