from patent_retrieval import PatentRetrievalPipeline, save_patents, load_patents

pipeline = PatentRetrievalPipeline()
patents = pipeline.run("CO")

# Persist results
save_patents(patents, query_smiles="CO")

# Reload later
results = load_patents(query_smiles="CO")

print(results)