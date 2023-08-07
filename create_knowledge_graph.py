from biocypher import BioCypher
from scheduling.adapters.adapter import (
    GitHubAdapter,
    GitHubAdapterNodeType,
    GitHubAdapterEdgeType,
    GitHubAdapterIssueField,
)

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
bc.write_nodes(adapter.get_nodes())
bc.write_edges(adapter.get_edges())

# Write admin import statement
bc.write_import_call()

# Summary
bc.summary()
