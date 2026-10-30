import ollama
from falkordb import FalkorDB 
import re
import sqlite3
from ddgs import DDGS
import json

#python -m pip install ollama falkordb ddgs
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
    result = graph.query("""MATCH (n {name: $name}) RETURN n.name""",params={"name": name})
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
def mem():
    # 1.search by subject 2.delete by ID 3.create new entry
    try:
        a = inputArr[1]
    except IndexError:
        print(" Invalid syntax",end="")
        print(f" {inputArr[0]} HERE-> _")
        exit()
    if inputArr[1]=="search":
        try:
            a1 = inputArr[2]
        except IndexError:
            print(" Invalid syntax",end="")
            print(f" {inputArr[0]} {inputArr[1]} HERE->")
            exit()
        cur.execute(f'SELECT * FROM "{modelName}" WHERE subject LIKE ?', (f"%{a1}%",))
        rows=cur.fetchall()
        print(f"found {len(rows)} entries")
        for row in rows:
            print(f"ID: {row[0]} , subject: {row[1]} , content = \"{row[2]}\" , created_at {row[3]} , source: {row[4]}")
    elif inputArr[1]=="delete":
        try:
            a1 = inputArr[2]
        except IndexError:
            print(" Invalid syntax",end="")
            print(f" {inputArr[0]} {inputArr[1]} HERE->")
            exit()
        try:
            a1=int(a1)
        except Exception:
            print("Invalid entry ID, needs to be an integer.")
            exit()
        cur.execute(f'SELECT * FROM "{modelName}" WHERE ID = ?',(a1,))
        row = cur.fetchone()
        try:
            test=row[0]
        except TypeError:
            print("No entries were found.")
            exit()
        print(f"ID: {row[0]} , subject: {row[1]} , content = \"{row[2]}\" , created_at {row[3]} , source: {row[4]}")
        conf=input("are you sure you want to delete this? \n")
        if conf.lower() == "yes":
            cur.execute(f'DELETE FROM "{modelName}" WHERE id = ?',(a1,))
            con.commit()
        elif conf.lower()=="no":
            print("nothing was deleted.")
    elif inputArr[1]=="new":
        try:
            a1 = inputArr[2]
        except IndexError:
            print(" Invalid syntax",end="")
            print(f" {inputArr[0]} {inputArr[1]} HERE->")
            exit()
        try:
            a2 = inputArr[3]
        except IndexError:
            print("Invalid syntax",end="")
            print(f" {inputArr[0]} {inputArr[1]} {inputArr[2]} HERE->")
        cur.execute(f'''INSERT INTO "{modelName}" (subject, content) VALUES (?, ?)''', (a1, a2))
        print(f" created entry with content \"{a2}\" and subject \"{a1}\" ")
        con.commit()
    else:
        print(f"Invalid syntax: {inputArr[0]} HERE-> {inputArr[1]}")
        exit()
        
def gra(userInput):
    name="John Pork"
    name1="John Pork"
    name2="GigaNigga"
    result = graph.query("""MATCH (n {name: $name}) RETURN n.name""",params={"name": name})
    if result is not []:
        print(f"Name {name} exists.")
    result = graph.query("""MATCH (n)-[r]->(m) WHERE a.name = $name1 AND b.name = $name2 RETURN a, r, b""",params={"name1":name1,"name2":name2})
    for row in result.result_set:
        print(f"{row[0]} -- {row[1]} -> {row[2]}")

def ser(userInput):
    words = userInput.split(maxsplit=1)
    # Remove the first word
    userInput = ''.join(words[1:])
    print(f"userinput without first word is {userInput}")
    search_query=userInput
    ddgs=DDGS()
    results = list(ddgs.text(query=search_query,region='us-en',safesearch='off',max_results=10))
    print("done")
    print(json.dumps(results, indent=4, ensure_ascii=False))
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
            

print("tools: \n ->graph \n ->database \n ->search the web\n")
userInput = input(">> ")
inputArr=userInput.split()
if userInput == "?":
    print("current commands list: \n database search content {content} \n database search subject {subject} \n database new {subject}, {content} \n database delete {ID}")
elif inputArr[0] == "database":
    mem()
elif inputArr[0]=="graph":
    print()
    gra(userInput)
elif inputArr[0]=="search":
    ser(userInput)
elif inputArr[0]=="start":
    strt()
else:
    print(f"Invalid syntax HERE->{userInput}")