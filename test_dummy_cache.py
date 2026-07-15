import logging
from patent_retrieval.models import PatentResult
from patent_retrieval.database import save_patents, load_patents
from workflows.nodes import retrieve_patents_node
from workflows.state import PatentAnalysisState

logging.basicConfig(level=logging.INFO)

# 1. Save dummy
dummy_patent = PatentResult(
    publication_number="EP1234567A1",
    title="Dummy Patent",
    source="Test"
)
save_patents([dummy_patent], query_smiles="DUMMY_SMILES")

# 2. Test node retrieval
state: PatentAnalysisState = {
    "smiles": "DUMMY_SMILES",
    "disease": "Pain",
    "target": "COX-2"
}

res = retrieve_patents_node(state)
print("Returned:", len(res.get("raw_patents", [])))
if len(res.get("raw_patents", [])) > 0:
    print("Title:", res["raw_patents"][0].title)
