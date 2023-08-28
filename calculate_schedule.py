# Every Tueday at noon, calculate the schedule for the next week and update the
# GitHub project accordingly.

from biocypher import BioCypher
from scheduling.adapters.adapter import (
    GitHubAdapter,
    GitHubAdapterNodeType,
    GitHubAdapterEdgeType,
    GitHubAdapterIssueField,
)
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view as swv

pd.set_option("display.max_columns", None)


def main():
    bc = BioCypher()

    node_types = [
        GitHubAdapterNodeType.ISSUE,
    ]

    node_fields = [
        GitHubAdapterIssueField.NUMBER,
        GitHubAdapterIssueField.TITLE,
        GitHubAdapterIssueField.BODY,
    ]

    edge_types = [
        GitHubAdapterEdgeType.PART_OF,
    ]

    adapter = GitHubAdapter(
        node_types=node_types,
        node_fields=node_fields,
        edge_types=edge_types,
    )

    bc.add_nodes(adapter.get_nodes())
    bc.add_edges(adapter.get_edges())

    dfs = bc.to_df()

    for name, df in dfs.items():
        print(name)
        print(df.head())

    ## Calculate timeslots

    all_clubs = dfs["club"]
    persons = dfs["person"]
    timeslots = dfs["timeslot"]
    # remove skipped row
    timeslots = timeslots[timeslots["id"] != "skipped"]

    # add column "is_free" to persons, as a vector of booleans representing
    # whether the person is free at the timeslot (as many as there are rows in
    # timeslots)
    persons["is_free"] = [
        [True for _ in range(len(timeslots))] for _ in range(len(persons))
    ]
    # custom is_free for slobentanzer (could be automated later): set first four
    # timeslots to False (of the entire vector)
    persons.loc[persons["id"] == "slobentanzer", "is_free"].iloc[0][:4] = [
        False for _ in range(4)
    ]
    # add column "schedule" to persons, collecting all individual attended clubs
    persons["schedule"] = [[] for _ in range(len(persons))]

    # filter rows only with status "To be scheduled" and "Scheduled", but not
    # "Unscheduled" or "Closed / Parked"
    clubs = all_clubs[
        (all_clubs["status"] == "To be scheduled")
        | (all_clubs["status"] == "Scheduled")
    ].copy()
    clubs["status"] = "To be scheduled"

    # randomize the order of the rows
    clubs = clubs.sample(frac=1).reset_index(drop=True)

    # prepend rows that were skipped last week ("Unscheduled")
    unscheduled_clubs = all_clubs[all_clubs["status"] == "Unscheduled"]
    clubs = pd.concat([unscheduled_clubs, clubs], ignore_index=True)

    # define start and end times for the lunch break
    lunch_start = datetime.strptime("12:00", "%H:%M")

    # row-wise through clubs
    for index, row in clubs.iterrows():
        # skip if scheduled
        if row["status"] == "Scheduled":
            continue

        # assign earliest timeslot available, if it does not run into the lunch
        # break
        duration = row["duration"]
        assignees = row["assignees"]

        # add saezrodriguez if not already in assignees
        if "saezrodriguez" not in assignees:
            assignees.append("saezrodriguez")

        # calculate the number of consecutive timeslots needed
        num_timeslots = int(duration / 15)

        # find a window num_timeslots consecutive True values in all rows

        # 2d array of "is_free" values, with rows corresponding to assignees
        # and columns corresponding to timeslots
        is_free_array = np.array(
            [
                persons[persons["id"] == assignee]["is_free"].iloc[0]
                for assignee in assignees
            ]
        )

        # sliding window view of the array, with window size assignees times
        # number of timeslots
        free_timeslots = swv(is_free_array, (len(assignees), num_timeslots))

        # aggregate each timeslot window into a single boolean value
        free_timeslots = [check.all() for check in free_timeslots[0]]

        # fill vector with False values to account for the ultimate timeslots
        # that do not have enough values to form a window of num_timeslots
        free_timeslots += [False for _ in range(num_timeslots - 1)]

        # if there is no block of True values of length num_timeslots, skip
        if not np.any(free_timeslots):
            # update status
            row["status"] = "Unscheduled"
            clubs.loc[index] = row
            print(f"{row['title']}: ----- Skipped -----")
            print(clubs.head())
            adapter.mutate_column(row["id"], row["status"])
            adapter.mutate_timeslot(row["id"], "Skipped")
            continue

        # get earliest timeslot from the index of the first True value
        earliest_timeslot = timeslots[free_timeslots].iloc[0]["id"]

        # if not skipped, assign the timeslot to the club
        club_name = row["title"]
        row["timeslot"] = earliest_timeslot
        end_timeslot = (
            datetime.strptime(earliest_timeslot, "%H:%M")
            + timedelta(minutes=15 * (num_timeslots - 1))
        ).strftime("%H:%M")
        for assignee in assignees:
            # set is_free to False for the timeslots of the event, keeping the
            # rest of the vector
            persons.loc[persons["id"] == assignee, "is_free"].iloc[0][
                timeslots[timeslots["id"] == earliest_timeslot]
                .index[0] : timeslots[timeslots["id"] == end_timeslot]
                .index[0]
                + 1
            ] = [False for _ in range(num_timeslots)]

            # update the schedule of the assignees
            timespan = (
                earliest_timeslot
                + " - "
                + (
                    datetime.strptime(earliest_timeslot, "%H:%M")
                    + timedelta(minutes=15 * num_timeslots)
                ).strftime("%H:%M")
            )
            persons.loc[persons["id"] == assignee, "schedule"].iloc[0].append(
                club_name + " " + timespan
            )

        row["status"] = "Scheduled"

        # update clubs dataframe
        clubs.loc[index] = row

        print(f"{row['title']}: ----- Scheduled -----")
        print(clubs[["title", "duration", "timeslot", "status"]])
        print(persons[["id", "is_free", "schedule"]])

        # update the github project using the updated clubs dataframe
        adapter.mutate_column(row["id"], row["status"])
        adapter.mutate_timeslot(row["id"], row["timeslot"])
        adapter.mutate_duration(row["id"], str(row["duration"]))

    # append the persons table in markdown format to the README.md, replacing
    # the previous table
    persons_md = persons[["id", "schedule"]].to_markdown(index=False, tablefmt="github")
    with open("README.md", "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith("## Current Schedule"):
                lines[
                    i + 1
                ] = f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                # delete all lines after i+1
                lines = lines[: i + 2]
                # append the persons table
                lines.append(persons_md)
                break

    with open("README.md", "w") as f:
        f.writelines(lines)


if __name__ == "__main__":
    main()
