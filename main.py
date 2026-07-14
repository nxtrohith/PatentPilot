import requests

url = "https://www.surechembl.org/api/search/structure"

payload = {
    "StructureSearchRequest": {
        "struct": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "structSearchType": "similarity",
        "maxResults": 10
    }
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

r = requests.post(url, json=payload, headers=headers)

print(r.status_code)
print(r.text)
