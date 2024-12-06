from timefold.solver.score import (constraint_provider, ConstraintFactory, Joiners,  HardMediumSoftScore, ConstraintCollectors)
from datetime import datetime
from .domain import Employee, Shift

# debug in python
# since we cannot debug in java...
def debug(*args):
    print(args)
    return True

def get_minute_overlap(shift1: Shift, shift2: Shift) -> int:
    return (min(shift1.end, shift2.end) - max(shift1.start, shift2.start)).total_seconds() // 60

def overlapping_in_minutes(first_start_datetime: datetime, first_end_datetime: datetime,
                           second_start_datetime: datetime, second_end_datetime: datetime) -> int:
    latest_start = max(first_start_datetime, second_start_datetime)
    earliest_end = min(first_end_datetime, second_end_datetime)
    delta = (earliest_end - latest_start).total_seconds() / 60
    return max(0, delta)

@constraint_provider
def define_constraints(constraint_factory: ConstraintFactory):
    return [
        # Hard constraints
        one_shift_per_day(constraint_factory),
        no_overlapping_shifts(constraint_factory),
        consecutive_employee_shift_assignments(constraint_factory),
        # Medium constraints
        penalize_unassigned_shift(constraint_factory),
    ]

def one_shift_per_day(constraint_factory: ConstraintFactory):
    return (constraint_factory
            .for_each_unique_pair(Shift,
                                  Joiners.equal(lambda shift: shift.employee.name),
                                  Joiners.equal(lambda shift: shift.start.date()))
            .penalize(HardMediumSoftScore.ONE_HARD)
            .as_constraint("Max one shift per day")
            )

def no_overlapping_shifts(constraint_factory: ConstraintFactory):
    return (constraint_factory
            .for_each_unique_pair(Shift,
                                  Joiners.equal(lambda shift: shift.employee.name),
                                  Joiners.overlapping(lambda shift: shift.start, lambda shift: shift.end))
            .penalize(HardMediumSoftScore.ONE_HARD, get_minute_overlap)
            .as_constraint("Overlapping shift")
            )

# we need to penalize in order to allow employees in shifts!
# penalize more the "priority" (extra priority shift) than common shifts
# https://docs.timefold.ai/timefold-solver/latest/responding-to-change/responding-to-change#overconstrainedPlanningWithNullValues
def penalize_unassigned_shift(factory: ConstraintFactory):
    return (factory.for_each_including_unassigned(Shift)
                   .filter(lambda shift: shift.employee is None)
                   .penalize(HardMediumSoftScore.ONE_MEDIUM)
                   .as_constraint("Unassigned Employee")
            )

# Penalize more than 5 consecutive shifts
# https://docs.timefold.ai/timefold-solver/latest/constraints-and-score/score-calculation#collectorsConsecutive
def consecutive_employee_shift_assignments(constraint_factory: ConstraintFactory):
    return (constraint_factory.for_each(Shift)
            .join(Employee, Joiners.equal(lambda shift: shift.employee, lambda employee: employee))
            .group_by(lambda shift, employee: shift.employee,
                      ConstraintCollectors.to_consecutive_sequences(
                          lambda shift, e: shift, lambda shift: shift.dayint))
            .flatten_last(lambda chain: chain.getConsecutiveSequences())
            .filter(lambda employee, shifts: shifts.getCount() > 3)
            #.filter(lambda x,y: debug(x,y))
            .penalize(HardMediumSoftScore.ONE_HARD, lambda employee, shifts: shifts.getCount())
            .as_constraint("Penalize more than 5 consecutive shifts")
            )

# Hard Penalize more than 5 shifts per week
def Xconsecutive_employee_shift_assignments(constraint_factory: ConstraintFactory):
    return (constraint_factory.for_each(Shift)
            .group_by(lambda shift: shift.employee.name, lambda shift: shift.weekofyear,
                      ConstraintCollectors.count(), ConstraintCollectors.min(lambda shift: shift.start))
            .filter(lambda employee, w, c, m: c > 3)
            #.filter(lambda x,y,z,w: debug(x,y,z,w))
            .penalize(HardMediumSoftScore.ONE_HARD, lambda employee, w, c, m: c)
            .as_constraint("Penalize more than 5 shifts")
            )
