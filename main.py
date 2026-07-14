from patent_retrieval import PatentRetrievalPipeline

pipeline = PatentRetrievalPipeline()
patents = pipeline.run("CO")

for p in patents:
    print(p.to_dict())
