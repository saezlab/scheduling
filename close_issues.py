# Monday evening, move all issues from Scheduled to Closed
from biocypher import BioCypher
from scheduling.adapters.adapter import (
    GitHubAdapter,
    GitHubAdapterNodeType,
    GitHubAdapterEdgeType,
    GitHubAdapterIssueField,
)
import pandas as pd

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

    # Filter issues with status "Scheduled"
    dfs
    scheduled_clubs = dfs["club"][dfs["club"]["status"] == "Scheduled"]

    # Move all issues from Scheduled to Closed
    for _id in scheduled_clubs["id"]:
        adapter.mutate_column(_id, "Closed / Parked")

    # Remove this week's schedule from README.md
    with open("README.md", "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith("## Current Schedule"):
                lines[
                    i + 1
                ] = "Next week's schedule will be posted on Tuesday at noon.\n"
                # delete all lines after i+1
                lines = lines[: i + 2]
                break

    with open("README.md", "w") as f:
        f.writelines(lines)


if __name__ == "__main__":
    main()
