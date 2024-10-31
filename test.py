import unittest


class TestResults(unittest.TestCase):
    def __init__(
        self,
        methodName="runTest",
        test_data=set(),
        max_conflicts=0,
        data=None,
        raw_data={},
        all_results=[],
        sections_to_check=set(),
        pts_type=None,

    ):
        super().__init__(methodName)
        self.test_data = test_data
        self.max_conflicts = max_conflicts
        self.results = all_results
        self.raw_data = raw_data
        self.data = data
        self.sections_to_check = sections_to_check
        self.pts_type = pts_type

    def test_all_sections_scheduled(self):
        original_sections = set(self.raw_data.keys())
        result_sections = {course[0] for course in self.results}

        missed = original_sections - result_sections
        duplicates = result_sections - original_sections

        assert len(result_sections) == len(original_sections), (
            f"Mismatch in length of original and results:"
            f"{len(result_sections)} of {len(original_sections)} expected sections"
        )

        self.assertFalse(missed, f"Missed sections: {missed}")
        self.assertFalse(duplicates, f"Duplicate sections: {duplicates}")


    def run_constraint_conflicts(self):
        conflicts = set()

        for section1, section2 in self.sections_to_check:

            section1_data = next((c for c in self.results if c[0] == section1), None)
            if not section1_data:
                continue
            section2_data = next((c for c in self.results if c[0] == section2), None)

            _, _, (days1, start1, end1) = section1_data
            _, _, (days2, start2, end2) = section2_data

            if set(days1) & set(days2) and (
                (start1 <= start2 < end1) or (start2 <= start1 < end2)
            ):
                conflicts.add(
                    (section1, (days1, start1, end1), section2, (days2, start2, end2))
                )

        if conflicts:
            print("\n\n     Conflict Report:")
            print(f"          Constraint: type?:")
            for section1, section2 in conflicts:
                print(f"               {section1} : {section1[1]}")
                print(f"               {section2} : {section2[1]}")

        self.assertFalse(conflicts)


    def scheduled_soft_constraints(self):
        if self.max_conflicts == 0:
            print(f"pts type: {self.pts_type}     max: {self.max_conflicts}     num conflicts: N/A")
            self.assertTrue(self.max_conflicts == 0)
            return
        
        conflicts = set()
        for sections in self.test_data:
            section1, section2 = sections

            section1_data = next((c for c in self.results if c[0] == section1), None)
            if not section1_data:
                continue
            section2_data = next((c for c in self.results if c[0] == section2), None)

            _, _, (days1, start1, end1) = section1_data
            _, _, (days2, start2, end2) = section2_data

            if set(days1) & set(days2) and (
                (start1 <= start2 < end1) or (start2 <= start1 < end2)
            ):
                conflicts.add(
                    ((section1, (days1, start1, end1)), (section2, (days2, start2, end2)))
                )

        print(f"pts type: {self.pts_type}     max: {self.max_conflicts}     num conflicts: {len(conflicts)}")
        if conflicts: 
            conflict_info = []
            for section1, section2 in conflicts:
                conflict_info.append(
                    f"{section1} & {section2}",
                )
            self.log_conflict(conflict_info)  # Log the conflict

        if len(conflicts) > self.max_conflicts:
            print("\n\n     Conflict Report:")
            print(f"          Constraint: {self.pts_type}:")
            for section1, section2 in conflicts:
                print(f"               {section1[0]} & {section2[0]}")
                print(f"                    {section1} : {section1[1]}")
                print(f"                    {section2} : {section2[1]}")
        self.assertTrue(len(conflicts) <= self.max_conflicts)


    def log_conflict(self, conflict_info):
        with open("conflicts.log", "a") as f: 
            f.write(f"{conflict_info}\n")