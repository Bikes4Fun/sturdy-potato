from dataclasses import dataclass, field
from collections import defaultdict
from itertools import combinations
from typing import TypeAlias, Tuple, Set, Dict
from types import MappingProxyType
from collections.abc import Mapping

# Type Aliases
TimeKey: TypeAlias = Tuple[str, int, int]
CRT: TypeAlias = Tuple[str, str, TimeKey]

"""
The dataclass could be removed and might not be worth the computational load. 
Benefits: 
    -Everything is completely immutable. Sets, dictionaries etc cannot be altered.
        This prevents ever having an accidental change to the data while performing repeated, extensive lookups.
    -Hashed. Everything is hashed. Computing everything into the Mapping/Frozen state takes O(n)
        but lookups are roughly O(1). This means that there is heavy computational load upon creation,
        but in cases where there will be one creation followed by many lookups,
        it could improve performance.
    -Since it guarantees that the original data computations is isolated and immutable, 
        I decided it was worth any tradeoffs to guarantee that I never needed
        to debug a dictionary that had been acidentaly altered while doing a lookup
        This decision came after realizing exactly that was happening in some cases where
        it appeared that I was only retrieving an item, when in fact because I was using
        defaultdict, and had errors where I was looking up items that didn't exist, I was altering
        my data in place which obviously was a nightmare to debug. 
        feel free to remove it if the cost/benefit isn't worth it. 
        You could comment out the dataclass and remove the setters and simply
        alter the getters to return the objects in ProcessData and compare performance. 
"""


@dataclass(frozen=False)
class Data:
    conflict_combinations: Mapping[int, Set[Tuple[CRT, CRT]]] = field(default_factory=dict)
    
    building_room_course: Mapping[str, Dict[TimeKey, Set]] = field(default_factory=dict)
    course_to_literal: Mapping[CRT, int] = field(default_factory=dict)
    courses_by_time: Mapping[TimeKey, Set[str]] = field(default_factory=dict)
    current_literal: int = 0
    literal_to_course: Mapping[int, CRT] = field(default_factory=dict)

    section_to_crt: Mapping[str, Set[CRT]] = field(default_factory=dict)
    time_conflicts: Mapping[TimeKey, Set[TimeKey]] = field(default_factory=dict)
    times_by_section: Mapping[str, Set[TimeKey]] = field(default_factory=dict)

class ProcessData:
    def __init__(self, course_data: Dict):

        self.all_sections: Set[str] = set()  # all course names "CS 2420-01"
        self.ampm_day_time: dict[tuple[int, str], set] = defaultdict(set)
        self.building_room_course = defaultdict(lambda: defaultdict(set))

        self.conflict_combinations = {
            100: set(),
            99: set(),
            60: set(),
            45: set(),
            32: set(),
            30: set(),
        }

        self.course_data = course_data
        self.courses_by_time = defaultdict(set)
        self.course_to_literal: dict[CRT, int] = defaultdict(int)
        self.current_literal = 1
        self.data = None

        self.literal_to_course: dict[int, CRT] = defaultdict(CRT)
        self.section_to_crt: dict[str, set[CRT]] = defaultdict(set)
        self.time_conflicts = defaultdict(set)
        self.times_by_section = defaultdict(set)

    def set_data(self):

        self.data = Data(
        
            conflict_combinations = MappingProxyType(dict(self.conflict_combinations)),
            building_room_course = MappingProxyType(dict(self.building_room_course)),
           
            course_to_literal = MappingProxyType(dict(self.course_to_literal)),
            courses_by_time = MappingProxyType(dict(self.courses_by_time)),
            current_literal = self.current_literal,

            literal_to_course = MappingProxyType(dict(self.literal_to_course)),
            section_to_crt = MappingProxyType(dict(self.section_to_crt)),
            time_conflicts = MappingProxyType(dict(self.time_conflicts)),
            times_by_section = MappingProxyType(dict(self.times_by_section)),
        )

    def get_data(self):
        return self.data
    

    def process_data(self):
        for section1, section2 in combinations(self.course_data.keys(), 2):
            if section1 not in self.all_sections:
                self.process_one_section(section1)
            if section2 not in self.all_sections:
                self.process_one_section(section2)
                            
            self.process_conflicts(min(section1, section2), max(section1, section2))
        
        self.process_date_times()
        self.set_data()
        return True
    

    def assign_literals(self, course_key: CRT) -> None:
        self.course_to_literal[course_key] = self.current_literal
        self.literal_to_course[self.current_literal] = course_key
        self.current_literal += 1
        return
    

    # format "("Smith 107", "MWF1000+150", 0)" to a tuple (days, start time, end time)
    def calculate_time_slot(self, time: str) -> TimeKey:
        x = time.index("+")
        days = time[: x - 4]
        start = int(time[x - 4 : x]) * 60
        end = int(time[x + 1 :]) * 60
        return (days, start, start + end)


    def process_one_section(self, section):
        self.all_sections.add(section)
        for room, time, _ in self.course_data[section]["room_times"]:
            time_slot = self.calculate_time_slot(time)
            course_key = (section, room, time_slot)

            self.assign_literals(course_key)

            section, building_room, time = course_key
            days = time[0]
            self.section_to_crt[section].add(course_key)

            for char in set(days):
                char_time = (char, time[1], time[2])
                self.building_room_course[building_room][char_time].add(course_key)
                self.courses_by_time[char_time].add(course_key)
                self.times_by_section[section].add(char_time)

                if time[1] <= 72000:
                    self.ampm_day_time[(0, char)].add(tuple([time[1], time[2]]))
                if time[2] >= 72000:
                    self.ampm_day_time[(1, char)].add(tuple([time[1], time[2]]))


    def process_date_times(self):
        for ampmday, times in self.ampm_day_time.items():
            day = ampmday[1]
            if len(times) == 1:
                time = next(iter(times))
                start, end = time
                self.time_conflicts[(day, start, end)].add((day, start, end))
                continue

            for time1, time2 in combinations(times, 2):

                start1, end1 = time1
                start2, end2 = time2
                time1 = (day, time1[0], time1[1])
                time2 = (day, time2[0], time2[1])
                self.time_conflicts[time1].add(time1)
                self.time_conflicts[time2].add(time2)

                if (start1 <= start2 <= end1) or (start2 <= start1 <= end2):
                    self.time_conflicts[time1].add(time2)
                    self.time_conflicts[time2].add(time1)


    def process_conflicts(self, section1, section2):

        for conflict_type, combinations in self.conflict_combinations.items():
            if ( section2 in self.course_data.get(section1)["hard"]
                or section1 in self.course_data.get(section2)["hard"]
            ):
                self.conflict_combinations[100].add((section1, section2))
            
            if (
                self.course_data[section1]["soft"].get(section2) == conflict_type
                or self.course_data[section2]["soft"].get(section1) == conflict_type
            ):
                combinations.add((section1, section2))


if __name__ == "__main__":
    pass
    # pd = ProcessData()
    # pd.process_data()
