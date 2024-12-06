from dataclasses import dataclass, field
from timefold.solver import SolverStatus
from timefold.solver.domain import *
from timefold.solver.score import HardMediumSoftScore
from datetime import datetime, date
from typing import Annotated, Optional, List, Set


@dataclass
class Employee:
    name: str
    skills: set[str]
    location: str
    # contract of user in hours
    contract: int
    unavailable_dates: Set[date] = field(default_factory=set)
    #undesired_dates: Annotated[set[date], Field(default_factory=set)]
    #desired_dates: Annotated[set[date], Field(default_factory=set)]
    # when 0 then user is not available on public holidays (will be used on a hard constrain)
    works_on_holiday: Optional[int] = 1 # By default we assume working on holidays
    stable_day_off: Optional[int] = 0  # When 1 uses specific_days_off
    specific_days_off: Set[int] = field(default_factory=set)  # Specific days off, Eg {6, 7} Saturday, Sunday
    stable_shift: Optional[int] = 0  # When 1 uses specific_shifts
    specific_shifts: Set[str] = field(default_factory=set) # Eg 07:00-15:00, 09:00-17:00
    custom_exceptions: List[dict] = field(default_factory=list)  # Custom exceptions

    def __init__(
        self,
        name: str,
        skills: Set[str],
        location: str,
        contract: int,
        unavailable_dates: Optional[Set[date]] = None,
        works_on_holiday: Optional[int] = 1,
        stable_day_off: Optional[int] = 0,
        specific_days_off: Optional[Set[int]] = None,
        stable_shift: Optional[int] = 0,
        specific_shifts: Optional[Set[str]] = None,
        custom_exceptions: Optional[List[dict]] = None,
    ):
        self.name = name
        self.skills = skills
        self.location = location
        self.contract = contract
        self.unavailable_dates = unavailable_dates or set()
        self.works_on_holiday = works_on_holiday
        self.stable_day_off = stable_day_off
        self.specific_days_off = specific_days_off or set()  # Default to empty set
        self.stable_shift = stable_shift
        self.specific_shifts = specific_shifts or set() # Default to empty set.
        self.custom_exceptions = custom_exceptions or []  # Default to empty list


    def __str__(self):
        return (
            f"Employee(name={self.name}, location={self.location}, skills={','.join(self.skills)}, "
            f"contract={self.contract} hours, unavailable_dates={','.join(map(str, self.unavailable_dates))}, "
            f"works_on_holiday={self.works_on_holiday}, "
            f"stable_day_off={self.stable_day_off}, specific_days_off={','.join(map(str, self.specific_days_off))}, "
            f"stable_shift={self.stable_shift}, specific_shifts={','.join(self.specific_shifts)}, "
            f"custom_exceptions={self.custom_exceptions})"
        )


@planning_entity
@dataclass
class Shift:
    id: Annotated[str, PlanningId]
    start: datetime
    end: datetime
    required_skill: str
    duration: int
    weekofyear: int
    # we are allowing unassigned values because we assume less people are available to handle the shifts
    # https://docs.timefold.ai/timefold-solver/latest/using-timefold-solver/modeling-planning-problems#planningVariableAllowingUnassigned
    employee: Annotated[Employee | None, PlanningVariable(allows_unassigned=True)] = field(default=None)
    # Pin entries that should not change, eg Stable_Shift and one Shift only
    # https://docs.timefold.ai/timefold-solver/latest/responding-to-change/responding-to-change#pinnedPlanningEntities
    pinned: Annotated[bool, PlanningPin] = field(default=False)

    def __init__(self, id: str, start: datetime, end: datetime, required_skill: str):
        self.id = id
        self.start = start
        self.end = end
        self.required_skill = required_skill
        self.duration = int((end - start).total_seconds() // 3600) # calculate the shift duration in hours
        self.weekofyear = start.isocalendar().week
        self.description = f"{start:%H:%M}-{end:%H:%M}" # Shift time eg 07:00
        self.dayint = start.timetuple().tm_yday

    def __str__(self):
        return (f'Shift(id={self.id} {self.start.strftime("%d/%m %H")}-{self.end.strftime("%H")} '
                f'{self.required_skill} {self.employee})')


@planning_solution
@dataclass
class EmployeeSchedule:
    employees: Annotated[list[Employee], ProblemFactCollectionProperty, ValueRangeProvider]
    shifts: Annotated[list[Shift], PlanningEntityCollectionProperty]
    score: Annotated[HardMediumSoftScore | None, PlanningScore] = field(default=None)
    solver_status: SolverStatus = field(default=None)

    def __init__(self, employees: list[Employee], shifts: list[Shift]):
        self.employees = employees
        self.shifts = shifts
