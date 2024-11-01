import cProfile, traceback, importlib, pstats, io
from itertools import combinations
from collections import defaultdict
from typing import Dict
from pysat.card import CardEnc


DATA = None
CURRENT_LITERAL: int
TOTAL_CLAUSES = 0
ALL_LITERALS = set()
DEBUG_CNF = True
DEBUG_CNF_LITERALS: Dict = defaultdict(set)
CHECKED = set()


def one_course_per_section():
    for section, courses in DATA.section_to_crt.items():
        course_lit = [DATA.course_to_literal[course] for course in courses]
        add_pair(course_lit, key=("one course per section", section))
        atmost_one(course_lit, key=("one course per section", section))


def profile_function(func):
    """Context manager to profile a specific function."""

    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable() 

        result = func(*args, **kwargs) 

        pr.disable()  

        stats = io.StringIO()
        ps = pstats.Stats(pr, stream=stats).sort_stats("cumulative")
        ps.print_stats()  # Print the profiling results

        print(stats.getvalue())  # Output the profiling results
        return result

    return wrapper

"""
iterate every building, every room in that building, and every timeslot that can exist in that room, mapped to every course that could be at that time. 

building_room_course["Smith 108"]['M', 66000, 69000)] = {('CS 1030-01', 'Smith 108', ('MWF', 66000, 69000)), ('CS 3150-01', 'Smith 108', ('MWF', 66000, 69000))...} 

for "Smith 108", ('M', 66000, 69000) in building_room_course

iterate every timeslot in that building/room, gather every course in a timeslot that conflicts with that time, where the course could be in that room during that conflicting timeslot. 

at most, one course from the current timeslot or any overlapping timeslot can exist at a time. 

there is a lot of duplicated checks here but a lot of the other versions I tried had items fall through. The issue with the simpler versions: 

Timeslot A: 9:00-10:30.
Timeslot B: 10:00-11:30.
Timeslot C: 11:00-12:00

Timeslot B conflicts with Timeslot A and Timeslot C. 
    therefore, no courses during timeslot B can exist with courses during timeslot A or timeslot C.

However, that doesn't mean Timeslot A and Timeslot C overlap.
So you can't just gather everything that overlaps with something
and make them all mututally exclusive. 

"""

# @profile_function
def only_one_per_room():
    for building_room, times in DATA.building_room_course.items():
        for time1, courses1 in times.items():
            # only times that are possible for this room,
            # and also conflicts with the current time need to be checked
            conflicting_room_times = DATA.time_conflicts[time1] & set(times)

            if courses1 and conflicting_room_times:
                for time2 in conflicting_room_times:
                    courses2 = DATA.building_room_course[building_room][time2]
                    if (tuple(courses1), tuple(courses2)) in CHECKED:
                        # print(f"duplicate {(tuple(courses1), tuple(courses2))}")
                        continue
                    else:
                        CHECKED.add((tuple(courses1), tuple(courses2)))
                    if courses2:
                        atmost_one(courses1, courses2, key=("room_literals"))


def no_hard_conflicts(combination_set, k=0, pts_key=None):
    global CURRENT_LITERAL
    if k == 0:
        return

    aux_var_set = []

    for section1, section2 in combination_set:
        courses1 = DATA.section_to_crt[section1]
        courses2 = DATA.section_to_crt[section2]

        # you only need to check times that are present in both sections.
        mutual_times = DATA.times_by_section[section1] | DATA.times_by_section[section2]

        for each_time in mutual_times:
            used_aux = False
            section1_conflicts = (
                DATA.time_conflicts[each_time] & DATA.times_by_section[section1])
            section2_conflicts = (
                DATA.time_conflicts[each_time] & DATA.times_by_section[section2])
            
            #  35226981    2.083    0.000    2.083    0.000 main.py:91(<genexpr>)
            conflicts1 = (
                set(
                    course
                    for time_conflict in section1_conflicts
                    for course in DATA.courses_by_time[time_conflict])
                & courses1)

            #  34831805    2.072    0.000    2.072    0.000 main.py:98(<genexpr>)
            conflicts2 = (
                set(
                    course
                    for time_conflict in section2_conflicts
                    for course in DATA.courses_by_time[time_conflict])
                & courses2)

            if len(conflicts1) < 1 or len(conflicts2) < 1:
                continue

            if k <= 1:
                atmost_one(
                    conflicts1, conflicts2, key=("atmost_one", pts_key, section1, section2))

            else:
                used_aux = True

                atmost_one(
                    conflicts1,
                    conflicts2,
                    aux_var=CURRENT_LITERAL,
                    k=k,
                    key=("atmost_one", pts_key, section1, section2, each_time),
                )

            # only inc the current literal if it was used for this timeslot
            # and only before the next set of sections
            if used_aux:
                aux_var_set.append(CURRENT_LITERAL)
                CURRENT_LITERAL += 1

    if k >= 1 and len(aux_var_set) > 1:
        sequential_k_greater_one(aux_var_set, k, pts_key=pts_key)

        # VERY VERY SLOW
        # totalizer_k_greater_one(aux_var_set, k, key=key)


def sequential_k_greater_one(aux_var_set, k, pts_key=None):
    global CURRENT_LITERAL
    # encoding = [1, 2 ...8]
    cnf = CardEnc.atmost(lits=aux_var_set, top_id=CURRENT_LITERAL, bound=k, encoding=3)
    max_literal = max(abs(lit) for clause in cnf for lit in clause)
    
    CURRENT_LITERAL = max(CURRENT_LITERAL, max_literal)
    add_pair(cnf, key=(pts_key, k, "sequential"))


"""
- can accept int literals or course variables that need to translate to their int literals.
- allows passing a single list where all items are mutually exclusive
- also allows passing two lists where items from list1 are exclusive to list2 but list1 is not exclusive to itself
    and list2 not exclusive to itself. this reduces duplicate clauses which seems to
    mostly help with printing the CNF moreso than running the actual solver.
"""
# @profile_function
def atmost_one(courses1, courses2=None, aux_var=None, k=1, key=None):
    pystat_current_lits = []

    # Translate variables to literals if they aren't integers
    # allowing the other functions to focus on gathering the items 
    # while this function handles generating the clauses
    def map_to_literal(item):
        return DATA.course_to_literal.get(item, item) if not isinstance(item, int) else item

    courses1_literals = [map_to_literal(i) for i in courses1]
    courses2_literals = [map_to_literal(j) for j in courses2] if courses2 else courses1_literals

    # Generate pairs between lists (or within a single list if courses2 is None)
    for i in courses1_literals:
        for j in courses2_literals:
            if courses2 == None:
                if i >= j:  # Ensure unique pairs (i, j) when using mutual exclusivity
                    continue
            if i == j:  # Skip pairs with identical literals
                continue
            
            # Construct clause
            clause = [-i, -j] if k == 1 else [-i, -j, aux_var]
            pystat_current_lits.append(clause)
            add_pair(clause, key=key)
    
    return pystat_current_lits

def add_pair(pair, key=None):
    global TOTAL_CLAUSES, DEBUG_CNF_LITERALS

    if all(isinstance(p, list) for p in pair):
        for sub_pair in pair:
            add_pair(sub_pair, key)
        return
    pair = tuple(pair)
    if pair in DEBUG_CNF_LITERALS[key] or pair in ALL_LITERALS:
        return
    if DEBUG_CNF:
        DEBUG_CNF_LITERALS[key].add(pair)
    else:
        ALL_LITERALS.add(pair)
    TOTAL_CLAUSES += 1


# about two seconds
def write_cnf() -> None:
    # Adjust according to how many chunks you want
    chunk_size = (max(len(DEBUG_CNF_LITERALS), len(ALL_LITERALS)) // 8) + 1

    # 512 KB buffer, adjust for your machine
    with open("results/output.cnf", "w", buffering=524288) as f:
        f.write(f"p cnf {CURRENT_LITERAL} {TOTAL_CLAUSES}\n")

        if DEBUG_CNF:
            for comment, data in DEBUG_CNF_LITERALS.items():
                f.write(f"c {comment} \n")
                chunk = [" ".join(map(str, clause)) + " 0\n" for clause in data]
                f.write("".join(chunk))
        else:
            print("standard cnf")
            all_list = list(ALL_LITERALS)
            for i in range(0, len(ALL_LITERALS), chunk_size):
                chunk = all_list[i : i + chunk_size]  
                buffer = [" ".join(map(str, clause)) + " 0\n" for clause in chunk]
                f.write("".join(buffer)) 


def main(course_data, constraints, debug) -> bool:
    global DATA, CURRENT_LITERAL, DEBUG_CNF
    
    DEBUG_CNF = debug
    DATA = course_data
    CURRENT_LITERAL = DATA.current_literal

    print(f"only one per room ... ")
    only_one_per_room()

    print(f"only one course per section...")
    one_course_per_section()

    print("no time conflicts ...")
    for pts_key, section_combinations in DATA.conflict_type_combinations.items():
        k_value = constraints[pts_key]
        if k_value > 0:  # Only call if the constraint is greater than 0
            no_hard_conflicts(section_combinations, k=k_value, pts_key=pts_key)

    write_cnf()

    return True


if __name__ == "__main__":
    # cProfile.run("main()")
    from process_data import ProcessData

    module = importlib.import_module("datasets.cs")
    importlib.reload(module)
    course_data = module.course_data

    pd = ProcessData(course_data)
    pd.process_data()
    DATA = pd.get_data()

    main(
        DATA,
        {"99": 1, "60": 1, "45": 1, "32": 1, "30": 0},
        True,
    )
