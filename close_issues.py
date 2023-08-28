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


if __name__ == "__main__":
    main()
