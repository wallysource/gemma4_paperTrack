lazy import ollama
lazy from falkordb import FalkorDB 
lazy import re
lazy import sqlite3
lazy from ddgs import DDGS
lazy import json
lazy from typing import Literal, Union
lazy from pydantic import BaseModel, Field
lazy import trafilatura
lazy import logging
lazy from datetime import datetime

#command to install all dependancies:
#python -m pip install ollama falkordb ddgs trafilatura
current_datetime_str = datetime.now().strftime("%d-%m-%y %H hours %M minutes,%S seconds")
logfile = open(f"D:/log {current_datetime_str}.log",'x')
logging.basicConfig(filename=f"log {current_datetime_str}.log",level=logging.INFO,format="%(asctime)s [%(levelname)s] %(message)s",datefmt="%Y/%m/%d %H:%M:%S")

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

class Databasenew(BaseModel):
    tool: Literal["database_new"]
    subject:str
    content:str
class Databasesearch(BaseModel):
    tool: Literal["database_search"]
    keyword:str
class Databasedelete(BaseModel):
    tool:Literal["database_delete"]
    id:int
class Graphexists(BaseModel):
    tool:Literal["graph_exists"]
    node_name:str
class Graphrelations(BaseModel):
    tool:Literal["graph_relations"]
    node_name:str
class Graphcreatenode(BaseModel):
    tool:Literal["graph_create_node"]
    node_name:str
class Graphlinknodes(BaseModel):
    tool:Literal["graph_link_nodes"]
    node_name_1:str
    node_name_2:str
    relationship:str
class Webfetch(BaseModel):
    tool:Literal["web_fetch"]
    url:str
class Websearch(BaseModel):
    tool:Literal["web_search"]
    keywords:str
class Scratchpadread(BaseModel):
    tool:Literal["scratchpad_read"]
class Scratchpadappend(BaseModel):
    tool:Literal["scratchpad_append"]
    info:str
class Scratchpadclear(BaseModel):
    tool:Literal["scratchpad_clear"]
class FinalResponse(BaseModel):
    tool:Literal["final_response"]
    response:str
class ToolCommand(BaseModel):
    command:Union[
        Websearch,
        Webfetch,
        Graphcreatenode,
        Graphexists,
        Graphlinknodes,
        Graphrelations,
        Databasedelete,
        Databasenew,
        Databasesearch,
        Scratchpadread,
        Scratchpadappend,
        Scratchpadclear,
        FinalResponse
    ] = Field(...,discriminator="tool")
inputArr="","",""

def get_llm_command(messages: list)->Union[Websearch,Webfetch,Graphcreatenode,Graphexists,Graphlinknodes,Graphrelations,Databasedelete,Databasenew,Databasesearch,Scratchpadread,Scratchpadappend,Scratchpadclear,FinalResponse]:
    response = ollama.chat(
        model=name,
        messages=messages,
        format=ToolCommand.model_json_schema(),
        options={"temperature": 0},
    )
    return ToolCommand.model_validate_json(response.message.content).command


#parsed function inputs

def database_search(keyword):
    success = True
    error="None"
    results=[]
    logging.info(f"database_search called with keyword {keyword}")
    try:
        cur.execute(f'SELECT * FROM "{modelName}" WHERE subject LIKE ? OR content LIKE ?', (f"%{keyword}%",))
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

def graph_link_nodes(node_name_1,node_name_2,relationship):
    error="None"
    success=True
    rel = re.sub(r"\W","_",relationship)
    logging.info(f"graph_link_nodes called with names {node_name_1} and {node_name_2} with relationship {relationship}")
    try:
        graph.query(f"""MERGE (a {{name:$name1}}) MERGE (b {{name:$name2}}) MERGE (a)-[r:{rel}]->(b) RETURN a,r,b""",params={"name1":node_name_1,"name2":node_name_2})
    except Exception as e:
        error=str(e)
        success = False
        logging.error(f"failed with error {e}")
    return {
            "success": success,
            "tool": "graph_link_nodes",
            "data": {
                "node_name_1": node_name_1,
                "node_name_2": node_name_2,
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
         "graph_link_nodes":(graph_link_nodes,{"node_name_1","node_name_2","relationship"}),
         "graph_create_node":(graph_create_node,{"node_name"}),
         "scratchpad_read":(scratchpad_read,{None}),
         "scratchpad_append":(scratchpad_append,{"info"}),
         "scratchpad_clear":(scratchpad_clear,{None})}


#parsing command
def command_parse(sonion):
    command = sonion.tool
    if command=="database_new":
        subject = sonion.subject
        content = sonion.content
        result=database_new(subject,content)
        return result
    elif command=="database_search":
        keyword = sonion.keyword
        result = database_search(keyword)
        return result
    elif command=="database_delete":
        id = sonion.id
        result=database_delete(id)
        return result
    elif command=="graph_exists":
        node_name = sonion.node_name
        result = graph_exists(node_name)
        return result
    elif command == "graph_relations":
        node_name = sonion.node_name
        result = graph_relations(node_name)
        return result
    elif command == "graph_create_node":
        node_name = sonion.node_name
        result = graph_create_node(node_name)
        return result
    elif command == "graph_link_nodes":
        node1 = sonion.node_name_1
        node2 = sonion.node_name_2
        relation = sonion.relationship
        result=graph_link_nodes(node1,node2,relation)
        return result
    elif command == "web_fetch":
        url = sonion.url
        result = web_fetch(url)
        return result
    elif command == "web_search":
        keywords = sonion.keywords
        result = web_search(keywords)
        return result
    elif command == "scratchpad_read":
        result = scratchpad_read()
        return result
    elif command == "scratchpad_append":
        info = sonion.info
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
                "You are an autonomous AI agent with access to tools. "
                "Use tools whenever necessary to fulfil the user's request. "
                "You may execute multiple tools in sequence. "
                "Examine each tool result before deciding what to do next. "
                "Only use final_response when you have enough information "
                "to answer the user."
            )
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    for iteration in range(10):

        # Ask LLM what to do next
        command = get_llm_command(messages)

        # Check whether the agent is finished
        if isinstance(command, FinalResponse):
            return command.response

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