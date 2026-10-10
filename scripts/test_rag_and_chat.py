import urllib.request
import urllib.parse
import json

# 1. Test RAG Search Endpoint
query = 'bearing lubrication sleeve bushing'
url = 'http://localhost:8000/api/rag/search?' + urllib.parse.urlencode({'q': query})
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as r:
    rag_res = json.loads(r.read().decode('utf-8'))

print('=== 1. RAG Search API Results ===')
print('Query:', rag_res['query'])
for hit in rag_res['results']:
    doc = hit.get('doc')
    title = hit.get('title')
    score = hit.get('score')
    snippet = hit.get('snippet', '')[:140].replace('\n', ' ')
    print(f'  [{doc}] - {title} (BM25 Score: {score})')
    print(f'   Snippet: {snippet}')

# 2. Test Copilot Chat API Endpoint
chat_payload = {
    'message': 'The motor is vibrating at 0.85g and temperature is 46C. What is the diagnosis and SOP recommendation?',
    'role': 'maintenance_engineer'
}
req2 = urllib.request.Request(
    'http://localhost:8000/api/chat',
    data=json.dumps(chat_payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req2) as r2:
    chat_res = json.loads(r2.read().decode('utf-8'))

print('\n=== 2. AI Copilot Chat Response ===')
print('Success:', chat_res.get('success'))
reply = chat_res.get('reply', '')
print('Full Reply:\n', reply)
