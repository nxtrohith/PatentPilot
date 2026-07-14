import requests

url = "https://www.surechembl.org/api/v3/api-docs"

r = requests.get(url)

print(r.status_code)

with open("surechembl_openapi.json", "w") as f:
    f.write(r.text)

print("Saved OpenAPI specification.")
