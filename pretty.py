from prettytable.colortable import ColorTable, Themes
from prettytable import ALL
from collections import defaultdict
import cProfile

PROFESSORS = {

}

def pretty_main(results) -> None:
    print_professors=True

    all_buildings = set()
    building_room_time = defaultdict(lambda: defaultdict(set))
    
    for course, room, time in results:
        building = room.split()[0]
        
        # not printing SET because too big
        if building.upper() == "SET":
            continue

        room = room.split()[1].strip()
        all_buildings.add(building)
        if "MW" in time[0]:
            time = list(time)
            time[0] = "MWF"
            time = tuple(time)
        building_room_time[building]["rooms"].add(room)
        building_room_time[building]["times"].add(time)
        building_room_time[building][(room, time)].add(course)


    for building, data in building_room_time.items():
        rooms = data["rooms"]
        times = data["times"]

        pt = ColorTable(theme=Themes.OCEAN)
        pt.align = "c"
        pt.hrules = ALL

        sorted_rooms = sorted([r for r in rooms])
        sorted_times = sorted([t for t in times])
        
        print(f"------------{building.upper()}------------------")
        pt.field_names = ["TIME↓ ROOM→"] + [room for room in sorted_rooms]

        for time in sorted_times:
            row = [f"{time}"]
            for room in sorted_rooms:
                cell = ""
                courses = building_room_time[building].get((room, time))
                if courses:
                    cell = "\n".join( course for course in courses)
                if print_professors:
                    for professor, data in PROFESSORS.items():
                        if cell in data:
                            cell = f"\033[1;{professor[1]}{cell}\033[0m" # color text
                row.append(cell)
            pt.add_row(row)
        print(pt)
        print("\n")

    # # Print rooms with only one course seperately to keep terminal cleaner
    # if print_singlerooms:
    #     print("Rooms with only one course scheduled:")
    #     for room, courses in rooms_with_one_course.items():
    #         course = next(iter(courses))  # Get the single course
    #         print(f"{room}: {course}")  # [0]} at {course[2][0]} {course[2][1]//60}")
    #     print("\n")

    
if __name__ == "__main__":

    cProfile.run("pretty_main(results)")




# # New code for printing the biology calendar
# for building, rooms_times in bio_building_room_time.items():
#     for day, times in sorted_times.items():
#         times = sorted(times)
#         for start_time in times:
#             row = [f"{day} {start_time}"]
#             for room in rooms:
#                 cell = ""  # Initialize cell for the current room
#                 if day == "MTWRF":
#                     # Include courses that are valid for all days
#                     cell = "\n".join(
#                         course
#                         for course, t in bio_room_to_course[(building, room)]
#                         if (
#                             set(t[0])
#                             <= set(
#                                 "MTWRF"
#                             )  # Check if the course is valid for MTWRF
#                             and t[1] / 60 == start_time
#                         )
#                         and course not in used  # Avoid duplicates
#                     )
#                 else:
#                     # Include courses for specific days
#                     cell = "\n".join(
#                         course
#                         for course, t in bio_room_to_course[(building, room)]
#                         if (
#                             set(t[0])
#                             <= set(
#                                 day
#                             )  # Only include courses that match the specific day
#                             and t[1] / 60 == start_time
#                         )
#                         and course not in used  # Avoid duplicates
#                     )

#                 # Update the used set with the courses added to the cell
#                 if cell:
#                     used.update(course for course in cell.split("\n") if course)
#                     if "BIOL 3250-01" in cell:
#                         cell = f"\033[1;31m{cell}\033[0m"  # Example: Red text for highlighting

#                 row.append(cell if cell else "")
#             if any(row[1:]):  # Only add row if it contains any courses
#                 pt.add_row(row)

#         print(pt)
#         print("\n")
# bio_courses = set() 
# bio_rooms = set()
# bio_times = set()
# bio_building_room_time = defaultdict( lambda: defaultdict(set) )  
# bio_room_to_course = defaultdict(set) 
# bio_soft = { "BIOL 3250-01", "BIOL 2300-01", "BIOL 3000R-09A", "BIOL 3040-01", "BIOL 3045-01", "BIOL 3100-01", "BIOL 3110-01", "BIOL 3420-01", "BIOL 3450-01", "BIOL 3460-01", "BIOL 4200-01", "BIOL 4205-01", "BIOL 4280-01", "BIOL 4350-01", "BIOL 4355-01", "BIOL 4440-01", "BIOL 4600-01", "BIOL 4605-01", "BIOL 4810R-01B", "BTEC 2020-01", "CHEM 3070-01", "CHEM 3075-01", "CHEM 3510-01", "CHEM 3520-01", "CHEM 4910-01", "ENVS 1210-01", "GEO 1110-01", "GEO 1115-01", "GEOG 3600-01", "GEOG 3605-01", "GEOG 4180-01", "PHYS 1010-01", "PHYS 2220-01",
# }