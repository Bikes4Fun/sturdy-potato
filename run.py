import os, pstats, cProfile, subprocess, importlib, traceback, logging, unittest
from contextlib import contextmanager
from typing import Iterator
from main import main
from pretty import pretty_main as pretty_main
from process_data import ProcessData
from test import TestResults

DATA = None
SOLVERS = {
    "cadical": None,
    "kissat": None
    }

class Solver:
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

    def solve(self):
        with self.managed_process() as process:
            if process.stdout is None:
                raise RuntimeError(f"No stdout from {self.solver}")
            
            parse = None
            if self.solver == "kissat":
                parse = self.parse_kissat
            else: parse = self.parse_generic

            for line in process.stdout:
                if "UNSATISFIABLE" in line:
                    logging.info(f"{line.strip()}\n")
                    return ["UNSATISFIABLE"]
                parse(line)
            
            if process.stderr.read():
                logging.error(f"Error from {self.solver}: {process.stderr.read()}")
                return False
        return True
    

    @contextmanager
    def managed_process(self) -> Iterator[subprocess.Popen[str]]:

        process = subprocess.Popen(
            [self.solver, "results/output.cnf"],
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


    def get_results(self) -> list:
        course_list = []
        for line in self.results:
            course = DATA.literal_to_course.get(int(line))
            if course:
                course_list.append(course)
        return sorted(course_list)
        

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

# --------  


def run_solver(solver_name) -> tuple:
    solver = Solver(solver_name)
    try:
        solver.solve() 

    except:
        traceback.print_exc()

    all_results:list = solver.get_results()
    return all_results


def run_tests(constraints, raw_data):
    suite = unittest.TestSuite()
    for solver, results in SOLVERS.items():
        suite.addTest(
            TestResults(
                "test_all_sections_scheduled", 
                all_results=results, 
                raw_data=raw_data, 
                data=DATA
                )
            )

        suite.addTest(
            TestResults(
                "run_constraint_conflicts", 
                all_results=results, 
                data=DATA
                )
            )

        for pts_type, test_data in DATA.conflict_type_combinations.items():
            suite.addTest(
                TestResults(
                    "scheduled_soft_constraints",
                    all_results=results,
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
    

    for solver_name in SOLVERS.keys():
        print(f"\nsolver: {solver_name}:")

        results = run_solver(
            solver_name)
        
        if not results:
            logging.info(f"solver: {solver_name} returned None or False {results}")
            print(f"solver: {solver_name} returned None or False {results}")
            traceback.print_stack()
        
        if "UNSATISFIABLE" in results:
            print("UNSATISFIABLE")
            continue
        
        print(f"running tests and printing results.")
        pretty_main(results)
        SOLVERS[solver_name] = results

    run_tests(constraints, raw_data)


def cleanup_files():
    """At the very end, clean up any files created during the run."""
    files_to_cleanup = ["results/output.cnf",]
    
    for file_path in files_to_cleanup:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)  
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
        "datasets.cs",
        
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
    
