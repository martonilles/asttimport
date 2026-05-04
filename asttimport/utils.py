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

NUM_PERIODS = 11


PRINT_INFO = True

def set_loglevel(print_info: bool = True):
    global PRINT_INFO
    PRINT_INFO = print_info

def info(*args):
    global PRINT_INFO
    if PRINT_INFO:
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


def parse_timeslots(data: str, debug: str = "") -> str | None:
    if not data:
        return None

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

    # info(f"Parsing timeslot '{data}'")
    try:
        for slot in data.split(","):
            slot = slot.strip()
            if not slot:
                continue

            if slot[0] in DAYS:
                day = DAYS.get(slot[0])
                if slot[1] in ("+", "-", "?"):
                    update(day=day, period=None, value=PREF_MAP.get(slot[1], "1"))
                else:
                    if len(slot) > 2 and slot[2].isdigit():
                        period = int(slot[1:3])
                        value = slot[3:]
                    else:
                        period = int(slot[1])
                        value = slot[2:]
                    update(
                        day=day, period=period, value=PREF_MAP.get(value, "1")
                    )
            elif slot[0].isnumeric():
                update(day=None, period=int(slot[0]), value=PREF_MAP.get(slot[1:], "1"))
    except Exception as e:
        error(f"Invalid timeslot '{data}' {e} {debug}")

    if prefs.intersection({"1", "0"}) == {"1", "0"}:
        error(f"Invalid timeslot default '{data}'")

    default = "0" if "1" in prefs else "1"

    timeoff = get_timeoff(timeslots, default)

    info(f"Parsed timeslots '{data}' -> '{timeoff}' {debug}")
    return timeoff


ALL_TIMESLOTS = parse_timeslots(",".join([f"{d}+" for d in DAYS.keys()]))
FACT_TIMESLOTS = parse_timeslots("1,2")
