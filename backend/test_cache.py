import logging
from dotenv import load_dotenv
from workflows.nodes import retrieve_patents_node
from workflows.state import PatentAnalysisState

logging.basicConfig(level=logging.INFO)
load_dotenv('.env')

state: PatentAnalysisState = {
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "disease": "Pain",
    "target": "COX-2"
}

res = retrieve_patents_node(state)
print("Returned:", len(res.get("raw_patents", [])))
