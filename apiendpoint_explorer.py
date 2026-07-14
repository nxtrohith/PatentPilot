import json

with open("surechembl_openapi.json") as f:
    spec = json.load(f)

for path in spec["paths"]:
    print(path)
