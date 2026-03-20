import requests

url = "http://localhost:11434/api/generate"

payload = {
    "model": "phi4-mini",   # your installed model
    "prompt": "Explain microservices in simple terms",
    "stream": False
}

response = requests.post(url, json=payload)

print(response.json()['response'])