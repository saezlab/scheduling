from biocypher import BioCypher
from scheduling.adapters.adapter import (
    GitHubAdapter,
    GitHubAdapterNodeType,
    GitHubAdapterEdgeType,
    GitHubAdapterIssueField,
)
from datetime import datetime, timedelta
import pandas as pd

pd.set_option("display.max_columns", None)


def main():
    # Instantiate the BioCypher interface
    # You can use `config/biocypher_config.yaml` to configure the framework or
    # supply settings via parameters below
    bc = BioCypher()

    # Choose node types to include in the knowledge graph.
    # These are defined in the adapter (`adapter.py`).
    node_types = [
        GitHubAdapterNodeType.ISSUE,
    ]

    # Choose protein adapter fields to include in the knowledge graph.
    # These are defined in the adapter (`adapter.py`).
    node_fields = [
        # Issues
        GitHubAdapterIssueField.NUMBER,
        GitHubAdapterIssueField.TITLE,
        GitHubAdapterIssueField.BODY,
    ]

    edge_types = [
        GitHubAdapterEdgeType.PART_OF,
    ]

    # Create a protein adapter instance
    adapter = GitHubAdapter(
        node_types=node_types,
        node_fields=node_fields,
        edge_types=edge_types,
        # we can leave edge fields empty, defaulting to all fields in the adapter
    )

    # Create a knowledge graph from the adapter
    bc.add_nodes(adapter.get_nodes())
    bc.add_edges(adapter.get_edges())

    dfs = bc.to_df()

    for name, df in dfs.items():
        print(name)
        print(df.head())

    # Summary
    # bc.summary()

    ## Calculate timeslots

    all_clubs = dfs["club"]
    timeslots = dfs["timeslot"]
    persons = dfs["person"]

    # add column "busy_until" to persons, default is first timeslot
    persons["busy_until"] = timeslots["id"].iloc[0]
    # add column "schedule" to persons, collecting all individual attended clubs
    persons["schedule"] = [[] for _ in range(len(persons))]

    # filter rows only with status "To be scheduled" and "Scheduled", but not
    # "Unscheduled" or "Closed / Parked"
    clubs = all_clubs[
        (all_clubs["status"] == "To be scheduled")
        | (all_clubs["status"] == "Scheduled")
    ]
    clubs["status"] = "To be scheduled"

    # randomize the order of the rows
    clubs = clubs.sample(frac=1).reset_index(drop=True)

    # prepend rows that were skipped last week ("Unscheduled")
    unscheduled_clubs = all_clubs[all_clubs["status"] == "Unscheduled"]
    clubs = pd.concat([unscheduled_clubs, clubs], ignore_index=True)

    # end time is last timeslot + 15 min
    end_time = datetime.strptime(timeslots["id"].iloc[-2], "%H:%M") + timedelta(
        minutes=15
    )

    # row-wise through clubs
    for index, row in clubs.iterrows():
        # skip if scheduled
        if row["status"] == "Scheduled":
            continue

        # assign earliest timeslot available
        duration = row["duration"]
        assignees = row["assignees"]
        # for each person in assignees get the busy_until
        busy_untils = []
        for assignee in assignees:
            busy_until = datetime.strptime(
                persons[persons["id"] == assignee]["busy_until"].iloc[0],
                "%H:%M",
            )
            busy_untils.append(busy_until)
        # get the latest busy_until as datetime
        latest_busy_until = max(busy_untils)

        # if the latest busy_until + duration is after end_time, skip
        if latest_busy_until + timedelta(minutes=duration) > end_time:
            # update status
            row["status"] = "Unscheduled"
            clubs.loc[index] = row
            print(f"{row['title']}: ----- Skipped -----")
            print(clubs.head())
            adapter.mutate_column(row["id"], row["status"])
            adapter.mutate_timeslot(row["id"], "Skipped")
            continue

        # if not skipped, assign the timeslot of the latest busy_until
        row["timeslot"] = datetime.strftime(latest_busy_until, "%H:%M")
        for assignee in assignees:
            # update the busy_until of the assignees
            persons.loc[
                persons["id"] == assignee, "busy_until"
            ] = datetime.strftime(
                latest_busy_until + timedelta(minutes=duration), "%H:%M"
            )
            # update the schedule of the assignees
            club_name = row["title"]
            timespan = (
                datetime.strftime(latest_busy_until, "%H:%M")
                + "-"
                + datetime.strftime(
                    latest_busy_until + timedelta(minutes=duration), "%H:%M"
                )
            )
            persons.loc[persons["id"] == assignee, "schedule"].iloc[0].append(
                club_name + " " + timespan
            )

        row["status"] = "Scheduled"

        # update clubs dataframe
        clubs.loc[index] = row

        print(f"{row['title']}: ----- Scheduled -----")
        print(clubs[["title", "duration", "timeslot", "status"]])
        print(persons[["id", "busy_until", "schedule"]])

        # update the github project using the updated clubs dataframe
        adapter.mutate_column(row["id"], row["status"])
        adapter.mutate_timeslot(row["id"], row["timeslot"])
        adapter.mutate_duration(row["id"], str(row["duration"]))

    # append the persons table in markdown format to the README.md, replacing
    # the previous table
    persons_md = persons[["id", "schedule"]].to_markdown(
        index=False, tablefmt="github"
    )
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
