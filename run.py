import os, pstats, cProfile, subprocess, importlib, traceback, logging, unittest
from contextlib import contextmanager
from typing import Iterator
from main import main
from pretty import pretty_main as pretty_main
from process_data import ProcessData
from test import TestResults

DATA = None
SOLVERS = ["cadical", "kissat"]

class Parser:
    """Parser for multiple SAT solvers with custom logic.
    Each solver outputs their results differently.
    As such, each parser is customized for the structure of their output.
    You can create the output.cnf and then use
    'solver output.cnf' in your terminal to see each solvers raw results.
    However, by using the parser it translates the output back into the course data
    """

    def __init__(self, solver):
        self.solver = solver
        self.results = []
        self.capturing = False
        self.num_lines = 0

    def parse(self, line):
        if self.solver == "kissat":
            self.parse_kissat(line)
        else:
            self.parse_generic(line)

    def parse_kissat(self, line: str):
        if "[ result ]" in line:
            self.capturing = True
        if self.capturing:
            if line.startswith("v"):
                self.results.extend(
                    [num for num in line.split()
                    if num.isdigit() and int(num) > 0]
                )            
            self.num_lines += 1
        if self.capturing and line.startswith("c") and self.num_lines > 2:
            self.capturing = False

    def parse_generic(self, line: str):
        if line.startswith("v"):
            self.results.extend(
                [num for num in line.split()
                if num.isdigit() and int(num) > 0]
            )

    def get_results(self, literal_to_course) -> list:

        course_list = []
        for line in self.results:
            course = literal_to_course.get(int(line))
            if course:
                course_list.append(course)
        return sorted(course_list)


@contextmanager
def managed_process(command: str, file: str) -> Iterator[subprocess.Popen[str]]:
    process = subprocess.Popen(
        [command, file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait()


def run_solver(solver_name, literal_to_course) -> tuple:
    p = Parser(solver_name)
    try:
        with managed_process(solver_name, "results/output.cnf") as process:
            if process.stdout is None:
                raise RuntimeError(f"No stdout from {solver_name}")

            for line in process.stdout:
                if "UNSATISFIABLE" in line:
                    logging.info(f"{line.strip()}\n")
                    return ["UNSATISFIABLE"]
                p.parse(line)

    except Exception as e:
        logging.error(f"Error while running {solver_name}: {e}")
        traceback.print_exc()

    all_results = p.get_results(literal_to_course)
    return all_results


def run_tests(all_results, constraints, raw_data, tests):
    suite = unittest.TestSuite()

    suite.addTest(
        TestResults(
            "test_all_sections_scheduled", 
            all_results=all_results, 
            raw_data=raw_data, 
            data=DATA
            )
        )

    suite.addTest(
        TestResults(
            "run_constraint_conflicts", 
            all_results=all_results, 
            data=DATA
            )
        )

    for pts_type, test_data in DATA.conflict_combinations.items():
        suite.addTest(
            TestResults(
                "scheduled_soft_constraints",
                all_results=all_results,
                max_conflicts=constraints[pts_type],
                pts_type=pts_type,
                test_data=test_data,
            )
        )

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def run_main(data: str, constraints: dict, tests: list, cnf_debug: bool) -> None:
    global DATA
    print(f"\nconstraints: {constraints}\ntests: {tests}\n")

    module = importlib.import_module(data)
    importlib.reload(module)
    raw_data = module.course_data

    pd = ProcessData(raw_data)
    pd.process_data()
    DATA = pd.get_data()

    if not DATA:
        logging.error(f"Error processing data in ProcessData: {DATA}")
        traceback.print_stack()
        return
    print(f"DATA was processed.")
    
    try:
        main(DATA, constraints, cnf_debug)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        traceback.print_stack()
    print(f"Main complete")
    
    # run solvers:
    for solver_name in SOLVERS:
        print(f"\nsolver: {solver_name}:")

        all_results = run_solver(
            solver_name, DATA.literal_to_course)

        if not all_results:
            logging.info(f"solver: {solver_name} returned None or False {all_results}")
            print(f"solver: {solver_name} returned None or False {all_results}")
            traceback.print_stack()
        
        if "UNSATISFIABLE" in all_results:
            print("UNSATISFIABLE")
            continue
        
        print(f"running tests and printing results.")
        pretty_main(all_results)
        run_tests(all_results, constraints, raw_data, tests)


def cleanup_files():
    """At the very end, clean up any files created during the run."""
    files_to_cleanup = ["results/output.cnf",]
    
    for file_path in files_to_cleanup:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)  # Delete the file
                print(f"Deleted file: {file_path}")
            else:
                print(f"File not found, skipping: {file_path}")
        except Exception as e:
            logging.error(f"Error deleting file {file_path}: {e}")


if __name__ == "__main__":
    pr = cProfile.Profile()
    pr.enable()
    run_main(

        # data to run (cset, cs, other)
        "datasets.cset",
        
        # constraints <= , 0=don't constrain
        {
        100: 1,
        99: 3, 
        60: 1, 
        45: 0, 
        32: 0, 
        30: 0
         },
        
        # test types to run
        [
        100,
        99,
        60,
        45,
        32,
        30,
        ],
        
        # write cnf file in debug mode ( verbose, comments, slow)
        True,
    )

    pr.disable()  # Stop profiling
    ps = pstats.Stats(pr)
    ps.strip_dirs().sort_stats("cumulative").print_stats(20)  # Print top 10 

    print(f"cleanup = False")
    # cleanup_files()
    




# future customizatoins:
# encoding type
# profiler on/off
# various solvers

# encoding types: 
# pairwise    = 0
# seqcounter  = 1
# sortnetwrk  = 2
# cardnetwrk  = 3
# bitwise     = 4
# ladder      = 5
# totalizer   = 6
# mtotalizer  = 7
# kmtotalizer = 8
# native      = 9