#!/usr/bin/env python3

import argparse
import clingo
import logging

logging.basicConfig()
log = logging.getLogger(__name__)


def on_model(m):
    log.debug(f'Model: {m}')


def scrub_file(input_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line and line[0] != '%']
        lines = [line.split('%')[0] for line in lines]
        lines = [line.strip() for line in lines]
    return lines


def parse_files(files):
    # Everything that is not a constraint will not be touched.
    other = []
    constraints = []
    for file in files:
        lines = scrub_file(file)
        i = 0
        while i < len(lines):
            log.log(5, "Iteration {}".format(i))
            statement = lines[i]
            while statement[-1] != '.':
                log.log(5, "Continuing statement {}".format(statement))
                assert i < len(
                    lines) - 1, "Incomplete statement in {}: {}".format(
                        file, statement)
                i += 1
                statement += lines[i]
            log.log(5, "New statement: {}".format(statement))
            if statement.startswith(':-'):
                constraints.append(statement)
            else:
                other.append(statement)
            i += 1
    log.log(5, "Other: {}".format("\n".join(other)))
    log.log(5, "Constraints {}".format("\n".join(constraints)))
    return other, constraints


def debug_files(files, check_full_problem=True):
    other, constraints = parse_files(files)
    # Check if the problem is completely satisfiable.
    ctl = clingo.Control()
    if check_full_problem:
        log.info("Checking whether complete program is satisfiable")
        program = "\n".join(other + constraints)
        log.log(6, program)
        ctl.add("base", [], program)
        ctl.ground([("base", [])])
        res = ctl.solve(on_model=on_model)
        if res.satisfiable:
            log.info("Complete problem is satisfiable, nothing to debug!")
            return
    # Check if there is a single constraint that results in UNSAT.
    found = False
    for i in range(len(constraints)):
        log.debug(f'Checking constraint {i}:\n{constraints[i]}')
        ctl = clingo.Control()
        program = "\n".join(other + constraints[:i] + constraints[i + 1:])
        ctl.add("base", [], program)
        ctl.ground([("base", [])])
        res = ctl.solve(on_model=on_model)
        if res.satisfiable:
            found = True
            log.info(f"Constraint {i} is unsatisfiable:\n{constraints[i]}")
    if not found:
        log.info(
            "Removing a single constraint does not make the problem satisfiable, giving up!"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='The file(s) to debug', nargs='+')
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        help='Verbose output')
    parser.add_argument(
        '-s',
        '--skip-full-problem',
        action='store_false',
        dest='check_full_problem',
        help='Skip checking whether the full problem is satisfiable')
    args = parser.parse_args()
    log.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    debug_files(args.file, args.check_full_problem)


if __name__ == '__main__':
    main()
