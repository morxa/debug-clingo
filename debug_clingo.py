#!/usr/bin/env python3

import argparse
import clingo
import logging
import os
import itertools

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


def get_num_steps(files):
    other, constraints = parse_files(files)
    return len(constraints)


def check_full_problem(other, constraints):
    ctl = clingo.Control()
    if check_full_problem:
        log.info("Checking whether complete program is satisfiable")
        program = "\n".join(other + constraints)
        log.log(6, program)
        ctl.add("base", [], program)
        ctl.ground([("base", [])])
        res = ctl.solve(on_model=on_model)
        return res.satisfiable


def debug_program(other, constraints, max_constraints=2):
    found = False
    for num_constraints in range(1, max_constraints + 1):
        for steps in itertools.combinations(range(len(constraints)),
                                            num_constraints):
            if debug_step(other, constraints, steps):
                found = True
        if found:
            break
        else:
            log.info(f'Removing {num_constraints} constraint(s)'
                     ' does not make the program satisfiable, trying more...')
    if not found:
        log.info(f'Removing up to {max_constraints} constraints'
                 ' does not make the program satisfiable, giving up!')


def debug_step(other, constraints, steps):
    steps = sorted(steps)
    log.debug('Checking constraint {}:\n{}'.format(
        steps, "\n".join([constraints[step] for step in steps])))
    ctl = clingo.Control()
    selected_constraints = []
    next_start = 0
    for step in steps:
        selected_constraints += constraints[next_start:step]
        next_start = step + 1
    selected_constraints += constraints[next_start:]

    program = "\n".join(other + selected_constraints)
    violating_constraints = [
        c for c in constraints if c not in selected_constraints
    ]
    ctl.add("base", [], program)
    ctl.configuration.solve.parallel_mode = min(os.cpu_count(), 64)
    ctl.configuration.solve.opt_mode = 'ignore'
    ctl.ground([("base", [])])
    res = ctl.solve(on_model=on_model)
    if res.satisfiable:
        log.info(f'Constraints {", ".join([str(s) for s in steps])}'
                 f' {"is" if len(violating_constraints) == 1 else "are"}'
                 ' unsatisfiable:\n' + '\n'.join(violating_constraints))
    return res.satisfiable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', help='The file(s) to debug', nargs='+')
    parser.add_argument('-v',
                        '--verbose',
                        type=int,
                        default=logging.INFO,
                        help='Verbose output level')
    parser.add_argument(
        '-s',
        '--step',
        type=int,
        help='Only run one specific step (remove constraint i); 1-indexed')
    parser.add_argument('--get-num-steps',
                        action='store_true',
                        help='Get the number of steps')
    parser.add_argument(
        '--skip-full-problem',
        action='store_false',
        dest='check_full_problem',
        help='Skip checking whether the full problem is satisfiable')
    parser.add_argument('-n',
                        '--num-constraints',
                        type=int,
                        default=1,
                        help='Number of constraints to remove')
    parser.add_argument('--outfile', '-o', help='Output file')
    args = parser.parse_args()
    log.setLevel(args.verbose)
    if args.outfile:
        fh = logging.FileHandler(args.outfile)
        log.addHandler(fh)
    if args.get_num_steps:
        log.setLevel(logging.ERROR)
        print(get_num_steps(args.files))
        return
    other, constraints = parse_files(args.files)
    if args.check_full_problem:
        if check_full_problem(other, constraints):
            log.info("Complete problem is satisfiable, nothing to debug!")
            return
        else:
            log.info("Complete problem is unsatisfiable, continuing...")
    if args.step:
        debug_step(other, constraints, [args.step])
    else:
        debug_program(other, constraints, args.num_constraints)


if __name__ == '__main__':
    main()
