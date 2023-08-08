# Club Scheduling

This repo implements a BioCypher pipeline that grabs all of the repo's issues,
which are organisational units of individual club meetings, and schedules them
into the available timeslots.

## Usage

The workflow in `.github/workflows/calculate_schedule.yml` is run periodically
on each Monday evening. It can also be triggered by push. It clones the
repository, installs the dependencies, and runs the `calculate_schedule.py`
script, which uses the BioCypher GitHub adapter in
`scheduling/adapters/adapter.py` to get the data and then computes the schedule
from the data.

### Scheduling

The scheduling algorithm is a simple greedy algorithm that iterates through the
clubs (i.e., the issues) in *random order* and assigns them to the first
available timeslot, given that all attendants (i.e. assignees) of the club are
available at that time. If no such timeslot exists, the club is postponed (to
the `Unscheduled` column) to next week. 

If the club has been successfully assigned, the corresponding issue is updated
with the assigned time and moved to the `Scheduled` column. The schedules of
each person are also appended to the bottom of the README file.

### Preparing for the next week

After the club meetings, cards that were successfully scheduled are
automatically removed back to the `To be scheduled` column for the next week.
If a club should not be scheduled for the next week, it can be moved to the
`Closed / Parked` column.

Assignees should be updated to reflect those that wish to attend the club in the
following week.

### Parking Clubs

If a club should not be scheduled for the coming week(s), the card can be moved
to the `Closed / Parked` column. The club will then be ignored by the scheduling
algorithm.

## Current Schedule
Last updated: 2023-08-08 23:00:20
| id              | schedule                                    |
|-----------------|---------------------------------------------|
| slobentanzer    | ['Meta 14:00-15:00', 'Methods 15:00-15:30'] |
| roramirezf      | ['Meta 14:00-15:00', 'Methods 15:00-15:30'] |
| PauBadiaM       | []                                          |
| LornaWessels    | []                                          |
| saezrodriguez   | ['Methods 15:00-15:30']                     |
| martingarridorc | ['Methods 15:00-15:30']                     |
| smuellerd       | []                                          |
| jtanevski       | []                                          |
| barbarazpc      | []                                          |