AI Tools – Persistent Memory & Tool Orchestration : gemma4_paperTrack

A Python-based tool orchestration system that extends the capabilities of local Large Language Models (LLMs) by providing access to external tools, persistent memory, knowledge graphs, and web access.

The system allows an LLM to interact with its environment through structured tool calls, retrieve previously stored information, establish relationships between concepts, and access up-to-date information from the internet.

Features

-> Persistent Memory: Store and retrieve information using an SQLite database, allowing knowledge to persist across conversations and iterations.
-> Knowledge Graph: Uses FalkorDB to create nodes and establish relationships between concepts, enabling associative information retrieval.
-> Web Search: Search the internet using DuckDuckGo.
-> Web Fetching: Extract readable content from webpages using Trafilatura.
-> Tool Orchestration: Allows the LLM to determine when and how to invoke available tools through structured JSON commands.
-> Local LLM Support: Uses Ollama to run and communicate with locally hosted language models.

Requirements

The following software must be installed before running the project:

1. Python 3.10+
2. Docker Desktop (or Docker Engine)
3. FalkorDB running inside Docker
4. Ollama installed and running locally
5. A compatible language model downloaded through Ollama.

Installation

1. Clone the repository


git clone https://github.com/wallysource/gemma4_paperTrack


2. Install Python dependencies

Run the following command:


python -m pip install ollama falkordb ddgs trafilatura


3. Set up FalkorDB using Docker

Make sure Docker is installed and running.

Pull the FalkorDB Docker image:

BASH:
docker pull falkordb/falkordb


Start a FalkorDB container:

BASH:
docker run -d \
  --name falkordb \
  -p 6379:6379 \
  -p 3000:3000 \
  falkordb/falkordb


FalkorDB should now be accessible locally through:

- Redis-compatible connection: `localhost:6379`
- Browser interface: `http://localhost:3000`

4. Set up Ollama

Download and install Ollama from:

https://ollama.com/

Pull a compatible model:

BASH:
ollama pull (model name)


For example:

BASH:
ollama pull gemma4:e2b


Make sure the Ollama service is running before starting the application.

#Running the Project

Once all dependencies and services are running, execute the main Python script:

BASH:
python fin.py

then type "llm" into the command section


The application will communicate with the local Ollama instance and use FalkorDB for graph-based memory operations.

Architecture

The system consists of three main components:

| Component           | Technology  | Purpose                                       |
|---------------------|-------------|-----------------------------------------------|
| LLM Interface       | Ollama      | Language model inference and tool selection   |
| Persistent Database | SQLite      | Long-term information storage and retrieval   |
| Knowledge Graph     | FalkorDB    | Associative relationships between information |
| Web Search          | DDGS        | Internet search                               |
| Web Extraction      | Trafilatura | Webpage content extraction                    |
| Orchestration       | Python      | Tool execution and coordination               |

Project Goals

The goal of this project is to explore how external memory, associative knowledge representation, and autonomous tool usage can improve the capabilities of locally hosted language models.

Particular emphasis is placed on persistent knowledge, information retrieval, and enabling smaller language models to work with information beyond their immediate context window.

[License]
no license do what you want with it :>