import ollama
from falkordb import FalkorDB 
import re
import sqlite3
from ddgs import DDGS
import json
import requests
from bs4 import BeautifulSoup

#command to install all dependancies:
#python -m pip install ollama falkordb ddgs beautifulsoup4 requests


inputArr="","",""

try:
    temp = ollama.ps()
except Exception:
    print("Ollama isn't running")
    exit()
t=[]
for data in temp.models:
    name = data.model
    modelName = re.split(r"[\W_]",name)[0]
    print(f"model: {modelName}")
if t == temp.models:
    print("no models are running")
    print("model will be assumed as \"gemma4\"")
    modelName="gemma4"
con = sqlite3.connect("brain.db")
cur = con.cursor()

cur.execute(f'''CREATE TABLE IF NOT EXISTS {modelName} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'user'
)''')
con.commit()
try:
    db=FalkorDB(host='localhost',port=6379)
    graph = db.select_graph(f'{modelName}')
except Exception:
    print("FalkorDB connection failed.")
def strt():
    done = False
    while not done:
        print()

#parsed function inputs

def database_search(keyword):
    cur.execute(f'SELECT * FROM "{modelName}" WHERE subject LIKE ?', (f"%{keyword}%",))
    rows=cur.fetchall()
    return rows

def database_new(subject,content):
    try:
        cur.execute(f'''INSERT INTO "{modelName}" (subject, content) VALUES (?, ?)''', (subject, content))
        con.commit()
    except Exception:
        return 0
    return 1

def database_delete(id):
    cur.execute(f'DELETE FROM "{modelName}" WHERE id = ?',(id,))
    con.commit()

def graph_exists(node_name):
    result = graph.query("""MATCH (n {name: $name}) RETURN n.name""",params={"name": node_name})
    if result is not []:
        return True
    else :
        return False
    
def graph_relations(node_name):
    result = graph.query("""MATCH (n)-[r]->(m) WHERE a.name = $node_name RETURN a, r, b""",params={"node_name":node_name})
    return result.result_set

def web_search(keywords):
    words = keywords.split(maxsplit=1)
    keywords = ''.join(words[1:])
    search_query=keywords
    ddgs=DDGS()
    results = list(ddgs.text(query=search_query,region='us-en',safesearch='off',max_results=10))
    return results

def web_fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unnecessary elements
        for tag in soup([
            "script", "style", "noscript",
            "nav", "footer", "header", "iframe"
        ]):
            tag.decompose()

        # Extract the page title
        title = soup.title.get_text(strip=True) if soup.title else "No title"

        # Extract readable text from the page
        text = soup.get_text(separator="\n", strip=True)

        return {
            "url": url,
            "title": title,
            "text": text
        }

    except requests.RequestException as e:
        return {
            "url": url,
            "error": str(e)
        }

tools = {"database_search": (database_search, {"keyword"}),
         "database_new":(database_new, {"subject","content"}),
         "database_delete":(database_delete, {"id"}),
         "graph_exists":(graph_exists, {"node_name"}),
         "graph_relations":(graph_relations, {"node_name"}),
         "web_search":(web_search, {"keywords"}),
         "web_fetch":(web_fetch, {"url"})}

def command_parse(command):
    try:
        command = json.loads(command)
        if not isinstance(command,dict):
            print("Invalid input, expected JSON")
            return 0
        tool =command.get("tool")
        args=command.get("arguments")
        if tool=="response":
            if not isinstance(args,dict):
                print("Error: invalid arguments")
                return 0
            message = args.get("message")
            if not isinstance(message,str):
                print("Error: message must be a string")
                return 0
    except json.JSONDecodeError:
        print("invalid JSON")
    except Exception as e:
        print(f"Error: {e}")

while True:
    a=input(">>> ")
    if a == "?":
        print(json.dumps(tools))
