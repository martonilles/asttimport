import csv
from collections import defaultdict, Counter
import sys
from ortools.sat.python import cp_model


def load(filename: str):
    diakok = defaultdict(list)

    cols = [
        '1. sáv',
        '2. sáv',
        '3. sáv',
        'extra',
    ]

    skiped_subjects = {
        "nem választok",
        # "vizuális kultúra"
    }


    with open(filename, mode='rt', encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            for col in cols:
                if row[col] and all(skipped not in row[col] for skipped in skiped_subjects):
                    diakok[row['E-mail-cím']].append(row[col])

    return diakok


def optimize_schedule_flexible(
    student_selections: dict[str, list[str]],
    subject_config: dict[str, dict[str, int]] = None,
    default_split_threshold: int = 20,
    default_max_teachers: int = 2,
    default_min_class_size: int = 0,  # Global default minimum
    default_max_class_size: int = 25,  # Global default maximum
    num_timeslots: int = 3,
):
    if subject_config is None:
        subject_config = {}

    model = cp_model.CpModel()

    # --- 1. PRE-PROCESS SUBJECTS & GROUPS ---
    all_requested_subjects = [
        sub for subs in student_selections.values() for sub in subs
    ]
    subject_demands = Counter(all_requested_subjects)

    subject_instances = {}
    teachers_per_subject = {}
    max_caps_per_subject = {}
    min_caps_per_subject = {}

    for subject, demand in subject_demands.items():
        config = subject_config.get(subject, {})
        threshold = config.get("split_threshold", default_split_threshold)
        max_teachers = config.get("max_teachers", default_max_teachers)

        # Fetch custom min/max sizes
        min_size = config.get("min_class_size", default_min_class_size)
        max_size = config.get("max_class_size", default_max_class_size)

        teachers_per_subject[subject] = max_teachers
        max_caps_per_subject[subject] = max_size
        min_caps_per_subject[subject] = min_size

        needed_groups = max(1, (demand + threshold - 1) // threshold)
        actual_groups = min(needed_groups, max_teachers)

        subject_instances[subject] = [
            f"{subject}_G{i+1}" for i in range(actual_groups)
        ]

    all_instances = [
        inst for insts in subject_instances.values() for inst in insts
    ]
    instance_to_subject = {
        inst: sub for sub, insts in subject_instances.items() for inst in insts
    }

    students = list(student_selections.keys())
    timeslots = list(range(1, num_timeslots + 1))

    # --- 2. DEFINE DECISION VARIABLES ---
    x = {}
    for s in students:
        for i in all_instances:
            for t in timeslots:
                x[s, i, t] = model.NewBoolVar(f"x_{s}_{i}_{t}")

    y = {}
    for i in all_instances:
        for t in timeslots:
            y[i, t] = model.NewBoolVar(f"y_{i}_{t}")

    # --- 3. CONSTRAINTS ---
    for s in students:
        for i in all_instances:
            for t in timeslots:
                model.Add(x[s, i, t] <= y[i, t])

    for i in all_instances:
        model.Add(sum(y[i, t] for t in timeslots) <= 1)

    for sub, insts in subject_instances.items():
        max_teachers = teachers_per_subject[sub]
        for t in timeslots:
            model.Add(sum(y[i, t] for i in insts) <= max_teachers)

    # Upper and Lower Bound Size Constraints
    for i in all_instances:
        base_subject = instance_to_subject[i]
        max_cap = max_caps_per_subject[base_subject]
        min_cap = min_caps_per_subject[base_subject]

        for t in timeslots:
            total_students_in_class = sum(x[s, i, t] for s in students)

            # Max size condition: total <= max_cap (implicitly bounded by y[i,t])
            model.Add(total_students_in_class <= max_cap)

            # Min size condition: If y[i,t] is active (1), then total >= min_cap
            # Enforced via: total >= min_cap * y[i, t]
            model.Add(total_students_in_class >= min_cap * y[i, t])

    for s in students:
        for t in timeslots:
            model.Add(sum(x[s, i, t] for i in all_instances) <= 1)

        for sub, insts in subject_instances.items():
            model.Add(
                sum(x[s, i, t] for i in insts for t in timeslots) <= 1
            )

        selected_subs = student_selections[s]
        for i in all_instances:
            if instance_to_subject[i] not in selected_subs:
                for t in timeslots:
                    model.Add(x[s, i, t] == 0)

    # --- 4. OBJECTIVE ---
    total_fulfilled = sum(
        x[s, i, t] for s in students for i in all_instances for t in timeslots
    )
    model.Maximize(total_fulfilled)

    # --- 5. SOLVE ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)

    # --- 6. DISPLAY RESULTS ---
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        timetable = {t: {} for t in timeslots}
        student_fulfilled_subjects = {s: [] for s in students}

        for i in all_instances:
            for t in timeslots:
                if solver.Value(y[i, t]) == 1:
                    assigned_students = [
                        s for s in students if solver.Value(x[s, i, t]) == 1
                    ]
                    timetable[t][i] = assigned_students
                    for s in assigned_students:
                        student_fulfilled_subjects[s].append(
                            instance_to_subject[i]
                        )

        total_requests = sum(len(subs) for subs in student_selections.values())
        fulfilled_count = int(solver.ObjectiveValue())
        unfulfilled_count = total_requests - fulfilled_count

        print("=== OPTIMIZATION SUMMARY ===")
        print(f"Total Requests: {total_requests}")
        print(f"Fulfilled Choices: {fulfilled_count}")
        print(f"Unfulfilled Choices: {unfulfilled_count}")
        print(
            f"Success Rate: {(fulfilled_count / total_requests) * 100:.2f}%\n"
        )

        print("=== TIMETABLE ===")
        for t in timeslots:
            print(f"\n--- Timeslot {t} ---")
            for inst, class_list in timetable[t].items():
                print(
                    f"  {inst} ({len(class_list)} students): {', '.join(class_list)}"
                )

        print("\n=== UNFULFILLED SELECTIONS REPORT ===")
        has_unfulfilled = False
        for s in students:
            requested = student_selections[s]
            fulfilled = student_fulfilled_subjects[s]
            unfulfilled = [sub for sub in requested if sub not in fulfilled]

            if unfulfilled:
                has_unfulfilled = True
                print(
                    f"  * {s} missed out on: {', '.join(unfulfilled)} "
                    f"(Requested: {len(requested)}, Got: {len(fulfilled)})"
                )

        if not has_unfulfilled:
            print("  🎉 Perfect fit! Every single student got all choices.")

        return timetable
    else:
        print("No feasible schedule found.")


def main():
    timetable = optimize_schedule_flexible(
            student_selections=load(sys.argv[1]),
            subject_config={
                "Janó-matematika": {"max_teachers": 1},
                "matematika": {"max_teachers": 1},
                "magyar nyelv és irodalom": {"min_class_size": 5},
            },
            default_split_threshold=11,  # Fallback for Science, English, etc.
            default_max_teachers=2,
            default_max_class_size=14,
            default_min_class_size=6,
            num_timeslots=3,
        )

    if timetable is not None:
        with open("fakt-out.csv", "w+") as f:
            csv_writer = csv.writer(f, dialect="excel", lineterminator="\n")
            csv_writer.writerow(("timeslot", "subject", "student"))
            for t, subjects_students in timetable.items():
                for subject, students in subjects_students.items():
                    for student in students:
                        csv_writer.writerow((t, subject, student))


