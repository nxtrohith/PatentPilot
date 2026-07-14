import requests

hash = "cfac8c8a-cfc9-44d3-91f4-c1cc3c7dd7f2"

url = f"https://www.surechembl.org/api/search/{hash}/status"

r = requests.get(url)

print(r.status_code)
print(r.text)
