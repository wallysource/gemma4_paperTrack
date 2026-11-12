import ollama
from falkordb import FalkorDB 
import re
import sqlite3
from ddgs import DDGS
import json
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
import trafilatura
import logging
from datetime import datetime
from pathlib import Path

#command to install all dependancies:
#python -m pip install ollama falkordb ddgs trafilatura

#creating logging files
LOG_DIR = Path("D:/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)   # create the folder if it doesn't exist

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_path = LOG_DIR / f"log_{timestamp}.log"

# to make a unique log if two runs start within the same second
n = 1
while log_path.exists():
    log_path = LOG_DIR / f"log_{timestamp}_{n}.log"
    n += 1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_path, mode="w", encoding="utf-8"),
        logging.StreamHandler(),   # also print to console; remove if unwanted
    ],
    force=True,
)

logging.info("Logging to %s", log_path)

#initialisation checks:
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
    logging.info("no models were running")
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
    logging.error("falkordb didnt connect")

#declaring command structure using pydantic

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class NoArgs(Strict):
    pass

# ---- arguments ----
class DatabaseNewArgs(Strict):
    subject: str
    content: str
class DatabaseSearchArgs(Strict):
    keyword: str
class DatabaseDeleteArgs(Strict):
    id: int
class NodeArgs(Strict):                 # reused by graph_exists / graph_relations / graph_create_node
    node_name: str
class GraphLinkArgs(Strict):
    base: str
    target: str
    relationship: str
class WebSearchArgs(Strict):
    keywords: str
class WebFetchArgs(Strict):
    url: str
class ScratchpadAppendArgs(Strict):
    info: str
class FinalArgs(Strict):
    response: str

# ---- commands ----
class Databasenew(Strict):
    tool: Literal["database_new"]
    arguments: DatabaseNewArgs
class Databasesearch(Strict):
    tool: Literal["database_search"]
    arguments: DatabaseSearchArgs
class Databasedelete(Strict):
    tool: Literal["database_delete"]
    arguments: DatabaseDeleteArgs
class Graphexists(Strict):
    tool: Literal["graph_exists"]
    arguments: NodeArgs
class Graphrelations(Strict):
    tool: Literal["graph_relations"]
    arguments: NodeArgs
class Graphcreatenode(Strict):
    tool: Literal["graph_create_node"]
    arguments: NodeArgs
class Graphlinknodes(Strict):
    tool: Literal["graph_link_nodes"]
    arguments: GraphLinkArgs
class Websearch(Strict):
    tool: Literal["web_search"]
    arguments: WebSearchArgs
class Webfetch(Strict):
    tool: Literal["web_fetch"]
    arguments: WebFetchArgs
class Scratchpadread(Strict):
    tool: Literal["scratchpad_read"]
    arguments: NoArgs
class Scratchpadappend(Strict):
    tool: Literal["scratchpad_append"]
    arguments: ScratchpadAppendArgs
class Scratchpadclear(Strict):
    tool: Literal["scratchpad_clear"]
    arguments: NoArgs
class FinalResponse(Strict):
    tool: Literal["response"]
    arguments: FinalArgs

Command = Annotated[
    Union[Databasenew, Databasesearch, Databasedelete,
          Graphexists, Graphrelations, Graphcreatenode, Graphlinknodes,
          Websearch, Webfetch,
          Scratchpadread, Scratchpadappend, Scratchpadclear,
          FinalResponse],
    Field(discriminator="tool"),
]
command_adapter = TypeAdapter(Command)
inputArr="","",""

def get_llm_command(messages: list)->Union[Websearch,Webfetch,Graphcreatenode,Graphexists,Graphlinknodes,Graphrelations,Databasedelete,Databasenew,Databasesearch,Scratchpadread,Scratchpadappend,Scratchpadclear,FinalResponse]:
    response = ollama.chat(
        model=name,
        messages=messages,
        format=command_adapter.json_schema(),
        options={"temperature": 0},
    )
    return command_adapter.validate_json(response.message.content)


#parsed function inputs

def database_search(keyword):
    success = True
    error="None"
    results=[]
    logging.info(f"database_search called with keyword {keyword}")
    try:
        cur.execute(f'''SELECT * FROM "{modelName}" WHERE subject LIKE ? OR content LIKE ?''', (f"%{keyword}%",f"%{keyword}%",))
        rows=cur.fetchall()
        counter=0
        for rel in rows:
            counter+=1
            results.append({f"entry {counter}":str(rel)})
    except Exception as e:
        error=str(e)
        success=False
        logging.error(f"search failed with error {e}")
    # for rel in result: print(rel)
    return {
                "success": success,
                "tool": "database_search",
                "data": {
                    "keyword": keyword,
                    "results":results if success else "Not determined"
                },
                "error": error
            }

def database_new(subject,content):
    error="None"
    success = True
    logging.info(f"database_new called with subject {subject} and content {content}")
    try:
        cur.execute(f'''INSERT INTO "{modelName}" (subject, content) VALUES (?, ?)''', (subject, content))
        con.commit()
    except Exception as e:
        error=str(e)
        success=False
        logging.error(f"failed with error {e}")
    return {
                "success": success,
                "tool": "database_new",
                "data": {
                    "subject": subject,
                    "content":content
                },
                "error": error
            }

def database_delete(id):
    success=True
    error="None"
    logging.info(f"database_delete called with id {id}")
    try:
        cur.execute(f'DELETE FROM "{modelName}" WHERE id = ?',(id,))
        con.commit()
    except Exception as e:
        error=str(e)
        success=False
        logging.error(f"failed with error {e}")
    post = cur.rowcount
    if 0==post:
        success=False
        cur.execute(f'''SELECT * FROM "{modelName}" WHERE id=?''',(id,))
        test = cur.fetchall()
        if test == None or test == []:
            error="No such entry was found"
        else:
            error = "delete failed"
    return {
                "success": success,
                "tool": "database_delete",
                "data": {
                    "id": id,
                },
                "error": error
            }

def graph_exists(node_name):
    success=True
    error="None"
    fin = False
    logging.info(f"graph_exists called with name {node_name}")
    try:
        result = graph.query("""MATCH (n {name: $name}) RETURN n.name""",params={"name": node_name})
        fin = len(result.result_set) > 0
    except Exception as e:
        error=str(e)
        success=False
        logging.error(f"failed with error {e}")
    return {
            "success": success,
            "tool": "graph_exists",
            "data": {
                "node_name": node_name,
                "Node Exists?": fin if success else "not determined"
            },
            "error": error
        }
    
def graph_relations(node_name):
    error="None"
    success=True
    results=[]
    logging.info(f"graph_relations called with node name {node_name}")
    try:
        result = graph.query("""MATCH (n)-[r]->(m) WHERE n.name = $node_name RETURN n.name, type(r), m.name""",params={"node_name":node_name})
        for row in result.result_set:
            results.append({
                "source": row[0],
                "relationship": row[1],
                "target": row[2]
            })
    except Exception as e:
            error=str(e)
            success = False
            logging.error(f"failed with error {e}")
    return {
        "success": success,
        "tool": "graph_relations",
        "data": {
            "node_name": node_name,
            "results": results
        },
        "error": error
    }

def graph_create_node(node_name):
    error="None"
    success=True
    logging.info(f"graph_create_node called with name {node_name}")
    try:
        graph.query("""MERGE (p {name:$name}) RETURN (p)""",params={"name":node_name})
    except Exception as e:
        error=str(e)
        success = False
        logging.error(f"failed with error {e}")
    return {
                "success": success,
                "tool": "graph_create_node",
                "data": {
                    "node_name": node_name,
                },
                "error": error
            }

def graph_link_nodes(base,target,relationship):
    error="None"
    success=True
    rel = re.sub(r"\W","_",relationship)
    logging.info(f"graph_link_nodes called with names {base} and {target} with relationship {relationship}")
    try:
        graph.query(f"""MERGE (a {{name:$name1}}) MERGE (b {{name:$name2}}) MERGE (a)-[r:{rel}]->(b) RETURN a,r,b""",params={"name1":base,"name2":target})
    except Exception as e:
        error=str(e)
        success = False
        logging.error(f"failed with error {e}")
    return {
            "success": success,
            "tool": "graph_link_nodes",
            "data": {
                "base": base,
                "target": target,
                "relationship":relationship
            },
            "error": error
        }

def web_search(keywords):
    error="None"
    success=True
    logging.info(f"web_search called with keywords {keywords}")
    try:
        search_query=keywords
        ddgs=DDGS()
        results = list(ddgs.text(query=search_query,region='us-en',safesearch='off',max_results=10))
    except Exception as e:
        success = False
        error=str(e)
        results=""
        logging.error(f"failed with error {e}")
    return {
        "success": success,
        "tool": "web_search",
        "data": {
            "keywords": keywords,
            "results": results
        },
        "error": error
    }

def web_fetch(url):
    error="None"
    success=True
    logging.info(f"web_search called with url {url}")
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
    except Exception as e:
        success=False
        text=""
        error=str(e)
        logging.error(f"failed with error {e}")
    if text is None:
        success=False
        text=""
        error="failed to extract text"
    return {
                "success":success,
                "tool":"web_fetch",
                "data":{
                    "url": url,
                    "text": text
                },
                "error": error
            }

def scratchpad_read():
    success=True
    error="None"
    logging.info("scratchpad_read called")
    original_content="Not Read"
    try:
        with open("D:/scratchpad.txt",'r', encoding='utf-8') as file:
            original_content = file.read()
    except Exception as e:
        error=str(e)
        success = False
        logging.error(f"failed with error {e}")
    return {
                "success":success,
                "tool":"scratchpad_read",
                "data":{
                    "contents": original_content,
                },
                "error": error
            }

def scratchpad_append(info):
    success = True
    error="None"
    logging.info(f"scratchpad_append called with info {info}")
    try:
        with open("D:/scratchpad.txt",'a', encoding='utf-8') as file:
            file.write(str(info)+"\n")
    except Exception as e:
        error=str(e)
        success = False
        logging.error(f"failed with error {e}")
    return {
                "success":success,
                "tool":"scratchpad_append",
                "data":{
                    "appended content": info,
                },
                "error": error
            }

def scratchpad_clear():
    success = True
    error="None"
    logging.info(f"scratchpad_clear called")
    try:
        with open("D:/scratchpad.txt",'w', encoding='utf-8') as file:
            pass
    except Exception as e:
        error = str(e)
        success = False
        logging.error(f"failed with error {e}")
    return {
                "success":success,
                "tool":"scratchpad_clear",
                "data":{
                    "None": "None",
                },
                "error": error
            }

tools = {"database_search": (database_search, {"keyword"}),
         "database_new":(database_new, {"subject","content"}),
         "database_delete":(database_delete, {"id"}),
         "graph_exists":(graph_exists, {"node_name"}),
         "graph_relations":(graph_relations, {"node_name"}),
         "web_search":(web_search, {"keywords"}),
         "web_fetch":(web_fetch, {"url"}),
         "graph_link_nodes":(graph_link_nodes,{"base","target","relationship"}),
         "graph_create_node":(graph_create_node,{"node_name"}),
         "scratchpad_read":(scratchpad_read,{None}),
         "scratchpad_append":(scratchpad_append,{"info"}),
         "scratchpad_clear":(scratchpad_clear,{None})}


#parsing command
def command_parse(sonion):
    command = sonion.tool
    if command=="database_new":
        subject = sonion.arguments.subject
        content = sonion.arguments.content
        result=database_new(subject,content)
        return result
    elif command=="database_search":
        keyword = sonion.arguments.keyword
        result = database_search(keyword)
        return result
    elif command=="database_delete":
        id = sonion.arguments.id
        result=database_delete(id)
        return result
    elif command=="graph_exists":
        node_name = sonion.arguments.node_name
        result = graph_exists(node_name)
        return result
    elif command == "graph_relations":
        node_name = sonion.arguments.node_name
        result = graph_relations(node_name)
        return result
    elif command == "graph_create_node":
        node_name = sonion.arguments.node_name
        result = graph_create_node(node_name)
        return result
    elif command == "graph_link_nodes":
        node1 = sonion.arguments.base
        node2 = sonion.arguments.target
        relation = sonion.arguments.relationship
        result=graph_link_nodes(node1,node2,relation)
        return result
    elif command == "web_fetch":
        url = sonion.arguments.url
        result = web_fetch(url)
        return result
    elif command == "web_search":
        keywords = sonion.arguments.keywords
        result = web_search(keywords)
        return result
    elif command == "scratchpad_read":
        result = scratchpad_read()
        return result
    elif command == "scratchpad_append":
        info = sonion.arguments.info
        result = scratchpad_append(info)
        return result
    elif command=="scratchpad_clear":
        result = scratchpad_clear()
        return result

#for agent and tool interaction
def agent(user_input):

    messages = [
        {
            "role": "system",
            "content": (
                f"""You are an autonomous AI agent with access to tools.

RULES
- Respond with exactly ONE tool call per message, as a single JSON object and nothing else (no markdown, no commentary).
- After each call you will receive the tool's result. Examine it before choosing your next action.
- You may make up to 30 tool calls in total for one request.
- ALWAYS write your plan to the scratchpad. After finishing each step, read the scratchpad and check the step off.
- Check the database for existing knowledge before searching the web. Store durable facts you learn.
- If a tool returns an error or nothing useful, try different arguments or another approach.
- Call response only when you have enough information to answer the user, or when you want to talk to the user or ask for information or awaiting commands.
- know that failure is an option, you are allowed to say you cant find anything in the database or graph but try to do it to the best of your ability

TOOLS

1. Database (long-term storage of facts; initially empty)
- database_new: {{"subject": str, "content": str}} -> creates an entry with id, timestamp, subject, content
- database_delete: {{"id": int}} -> deletes the entry with that id
- database_search: {{"keyword": str}} -> returns all entries whose subject or content match

2. Graph (nodes are people, places, things, or concepts; named edges describe relationships; initially empty but may contain information from earlier prompts)
- graph_exists: {{"node_name": str}} -> returns true/false
- graph_relations: {{"node_name": str}} -> returns all relationships of the node
- graph_create_node: {{"node_name": str}} -> creates a node
- graph_link_nodes: {{"base": str, "target": str, "relationship": str}} -> creates an edge from base to target with that label (both nodes may exist if not they are created)

3. Web
- web_search: {{"keywords": str}} -> top 10 results (url, title, snippet)
- web_fetch: {{"url": str}} -> returns the page content

4. Scratchpad (short-term memory; initially empty but may contain something from earlier prompts)
- scratchpad_read: {{}} -> returns contents
- scratchpad_append: {{"info": str}} -> appends text
- scratchpad_clear: {{}} -> clears it

5. response: {{"response": str}} -> sends your answer to the user, use this to ask the user for information or if youre awaiting instructions use the final response tool and ask the user.

OUTPUT FORMAT (valid JSON, double quotes, no trailing commas)
{{"tool": "database_new", "arguments": {{"subject": "ULTRAKILL", "content": "A game made by Arsi Hakita Patala"}}}}
{{"tool": "scratchpad_append", "arguments": {{"info": "PLAN: 1:search web 2:store facts 3:answer , search web DONE"}}}}
"""
            )
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    for iteration in range(30):

        # Ask LLM what to do next
        command = get_llm_command(messages)

        # Check whether the agent is finished
        if isinstance(command, FinalResponse):
            return command.arguments.response

        # Execute selected tool
        result = command_parse(command)

        # Give the LLM the result
        messages.append({
            "role": "assistant",
            "content": command.model_dump_json()
        })

        messages.append({
            "role": "user",
            "content": f"Tool result: {json.dumps(result)}"
        })
    return "I couldn't complete the request within the tool-use limit."

#user commands
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
            print(json.dumps(result, indent=4))
        elif a=="database_delete":
            v1 = int(input("enter ID of entry to delete: "))
            result=database_delete(v1)
            print(json.dumps(result, indent=4))
        elif a=="database_new":
            v1 = input("enter subject of new entry: ")
            v2 = input("enter content of new entry: ")
            result=database_new(v1,v2)
            print(json.dumps(result, indent=4))
        elif a=="graph_exists":
            v1 = input("enter node name: ")
            result=graph_exists(v1)
            print(json.dumps(result, indent=4))
        elif a=="graph_relations":
            v1 = input("enter a node name: ")
            result = graph_relations(v1)
            print(json.dumps(result, indent=4))
        elif a=="web_fetch":
            v1 = input("enter URL: ")
            result = web_fetch(v1)
            print(json.dumps(result, indent=4))
        elif a=="web_search":
            v1 = input("enter search keyword (stuff like searching for \"IPhone\" wont work with any other variation of capital\\small letters): ")
            result = web_search(v1)
            print(json.dumps(result, indent=4))
        elif a=="scratchpad_read":
            result = scratchpad_read()
            print(json.dumps(result,indent=4))
        elif a=="scratchpad_append":
            v1 = input("enter something to append: ")
            result = scratchpad_append(v1)
            print(json.dumps(result,indent=4))
        elif a=="scratchpad_clear":
            result = scratchpad_clear()
            print(json.dumps(result,indent=4))
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
            response = agent(inp)
            print(response)
    else:
        print("unknown command, type \"?\" for commands list")