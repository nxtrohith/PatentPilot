import logging
from dotenv import load_dotenv

# Set up logging so you can watch the pipeline progress
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(name)s — %(message)s'
)

# Load API keys from .env
load_dotenv('.env')

# Import our new workflow
from workflows import build_patent_workflow

# 1. Build and compile the graph
app = build_patent_workflow()

# 2. Define your initial input state
initial_state = {
    "smiles": "Cn1cnc2n(C)c(=O)n(C)c(=O)c12",  # Caffeine
    "disease": "Asthma",
    "target": "5-Lipoxygenase (5-LO)",
    "top_n": 5
}

print("=== Starting LangGraph Pipeline ===")

# 3. Invoke the graph (this will run retrieval -> enrichment -> analysis -> report)
final_state = app.invoke(initial_state)

print("\n=== Pipeline Complete ===\n")

# 4. Access the final structured report from the state
report = final_state.get("report")
errors = final_state.get("errors", [])

if errors:
    print("WARNING - Encountered the following errors during execution:")
    for error in errors:
        print(f" - {error}")

if report:
    print("RECOMMENDATION:", report.overall_recommendation.value)
    print("\nEXECUTIVE SUMMARY:")
    print(report.executive_summary)
    if report.key_similar_patents:
        print("\nKEY SIMILAR PATENTS:")
        for patent in report.key_similar_patents:
            print(f" - {patent}")
