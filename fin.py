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
    name = "gemma4:e2b"
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
    result = graph.query("""MATCH (n)-[r]->(m) WHERE n.name = $node_name RETURN n.name, type(r), m.name""",params={"node_name":node_name})
    return result.result_set

def graph_create_node(node_name):
    print()

def graph_link_nodes(node_name_1,node_name_2,relationship):
    print()

def web_search(keywords):
    search_query=keywords
    ddgs=DDGS()
    results = list(ddgs.text(query=search_query,region='us-en',safesearch='off',max_results=10))
    return results
    #returns 'title':title,'href':url and 'body':idk some text

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

def command_parse(sonion):
    print()
    command = sonion.get("command")
    args = sonion.get("argument")
    if command=="database_new":
        subject = args.get("subject")
        content = args.get("content")
        database_new(subject,content)
    if command=="database_search":
        keyword = args.get("keyword")
        results = database_search(keyword)
        return results
    if command=="database_delete":
        id = args.get("id")
        database_delete(id)
    if command=="graph_exists":
        node_name = args.get("node_name")
        result = graph_exists(node_name)
        return result
    if command == "graph_relations":
        node_name = args.get("node_name")
        results = graph_relations(node_name)
    if command == "graph_create_node":
        node_name = args.get("node_name")
        graph_create_node(node_name)
    if command == "graph_link_nodes":
        node1 = args.get("node_name_1")
        node2 = args.get("node_name_2")
        relation = args.get("relation")
        graph_link_nodes(node1,node2,relation)
    if command == "web_fetch":
        url = args.get("url")
        result = web_fetch(url)
    if command == "web_search":
        keywords = args.get("keywords")
        result = web_search(keywords)

def u():
    done = False
    while not done:
        a=input(">>> ")
        if a == "?":
            for row in tools:
                print(row)
        elif a=="database_search":
            v1 = input("enter content to search: ")
            result = database_search(v1)
            for rel in result:
                print(rel)
        elif a=="database_delete":
            v1 = int(input("enter ID of entry to delete: "))
            database_delete(v1)
        elif a=="database_new":
            v1 = input("enter subject of new entry: ")
            v2 = input("enter content of new entry: ")
            database_new(v1,v2)
        elif a=="graph_exists":
            v1 = input("enter node name: ")
            if graph_exists(v1):
                print("that node exists.")
            else:
                print("that node doesn't exist.")
        elif a=="graph_relations":
            v1 = input("enter a node name: ")
            if graph_exists(v1):
                results = graph_relations(v1)
                for row in results.result_set:
                    print(f"{row[0]}--{row[1]}->{row[2]}\n")
            else:
                print("no node of that name exists.")
        elif a=="web_fetch":
            v1 = input("enter URL: ")
            result = web_fetch(v1)
            print(f"URL: {result['url']}")
            print(f"Title: {result['title']}")
            print(f"Text Preview (first 300 chars): {result['text'][:300]}...")
        elif a=="web_search":
            v1 = input("enter search keyword (stuff like searching for \"IPhone\" wont work with any other variation of capital\\small letters): ")
            result = web_search(v1)
            for res in result:
                print(f"Title: {res['title']}\nURL: {res['href']}\nBody: {res['body']}\n\n")
        elif a=="exit":
            done=True
        else:
            print("not a valid command.")
thinkin = True
done = False
while not done:
    usr = input("enter a command: ")
    if usr == "?":
        print("command : command line to test tools")
        print("llm : connect to available llm")
    elif usr=="command":
        u()
    elif usr == "llm":
        finished = False
        while not finished:
            inp = input(">>> ")
            if inp.lower()=="exit":
                finished = True
                done = True
                break
            response = ollama.chat(model=f"{name}",messages=[{"role": "user", "content": f"{inp}"}],stream=True)
            for bit in response:
                if bit.message.thinking:
                    print(f"\033[90m{bit.message.thinking}\033[0m",end="",flush=True)
                    thinkin=True
                if bit.message.content:
                    if thinkin==True:
                        thinkin=False
                        print("")
                    print(bit.message.content,end="",flush=True)
            print()
    else:
        print("unknown command, type \"?\" for commands list")