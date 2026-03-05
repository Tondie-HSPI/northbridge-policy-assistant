import os, json, hashlib, operator
import numpy as np
import pandas as pd
from pathlib import Path
from pypdf import PdfReader
from typing import TypedDict, List, Annotated
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END

BASE_DIR      = Path(__file__).parent
DATA_DIR      = BASE_DIR / "data"
DOCUMENTS_DIR = BASE_DIR / "documents"

def load_csv_as_text(df, name): return f"[{name}]\n" + df.to_string(index=False)
def load_pdf_as_text(path):
    reader = PdfReader(str(path))
    return "\n\n".join(f"[Page {i+1}]\n{p.extract_text()}" for i, p in enumerate(reader.pages) if p.extract_text())

def load_all_documents():
    docs = []
    for name, path in [("fundraising_history", DATA_DIR/"northbridge_fundraising_history.csv"),("partner_intake_reports", DATA_DIR/"northbridge_partner_intake_reports.csv"),("volunteer_roster", DATA_DIR/"northbridge_volunteer_roster.csv")]:
        docs.append({"source": name, "text": load_csv_as_text(pd.read_csv(path), name)})
    for pdf_path in DOCUMENTS_DIR.rglob("*.pdf"):
        docs.append({"source": pdf_path.name, "text": load_pdf_as_text(pdf_path)})
    print(f"✓ {len(docs)} documents loaded.")
    return docs

def chunk_text(text, source, size=500, overlap=50):
    words, chunks, start = text.split(), [], 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append({"source": source, "text": " ".join(words[start:end])})
        if end == len(words): break
        start += size - overlap
    return chunks

class BM25Retriever:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.corpus = [t.lower().split() for c in chunks for t in [c["text"]]]
        N = len(self.corpus); avgdl = sum(len(d) for d in self.corpus) / max(N,1)
        df = {}
        for doc in self.corpus:
            for t in set(doc): df[t] = df.get(t,0)+1
        self.idf = {t: np.log((N-f+0.5)/(f+0.5)+1) for t,f in df.items()}
        self.avgdl = avgdl

    def retrieve(self, query, top_k=5):
        scores = []
        for i, doc in enumerate(self.corpus):
            dl = len(doc); freq = {}
            for t in doc: freq[t] = freq.get(t,0)+1
            score = sum(self.idf.get(t,0)*(freq.get(t,0)*(self.k1+1))/(freq.get(t,0)+self.k1*(1-self.b+self.b*dl/self.avgdl)) for t in query.lower().split())
            scores.append((i, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        top_score = scores[0][1] if scores else 0
        return [self.chunks[i] for i,_ in scores[:top_k]], top_score

print("Loading documents...")
DOCS = load_all_documents()
ALL_CHUNKS = [c for doc in DOCS for c in chunk_text(doc["text"], doc["source"])]
RETRIEVER = BM25Retriever(ALL_CHUNKS)
print(f"✓ {len(ALL_CHUNKS)} chunks indexed.\n")

@tool
def search_documents(query: str) -> str:
    """Search Northbridge internal documents. Always call before answering factual questions."""
    chunks, top_score = RETRIEVER.retrieve(query, top_k=5)

    if top_score < 1.0:
        return "INSUFFICIENT_DOCUMENTATION: No relevant internal documents found. Escalate to senior staff."

    if top_score >= 8.0:
        confidence = "High"
    elif top_score >= 4.0:
        confidence = "Medium"
    else:
        confidence = "Low"

    results = "\n\n---\n\n".join(f"[Source {i+1}: {c['source']}]\n{c['text']}" for i,c in enumerate(chunks))
    return f"CONFIDENCE: {confidence}\n\n{results}"

TOOLS = [search_documents]
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(TOOLS)

SYSTEM_PROMPT = """You are the Northbridge Policy Assistant.
Always call search_documents before answering factual questions.
Always respond in a professional, compassionate tone consistent with Northbridge's brand voice.
The tool will return a CONFIDENCE level (High, Medium, or Low) at the top of the results.
You MUST always end every answer with: 'Confidence: [level]'
If the tool returns INSUFFICIENT_DOCUMENTATION, respond with:
'I don't have enough documentation to answer this accurately. 🚨 This should be escalated to senior staff.'
Cite sources. Never invent facts."""

class State(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]

def assistant_node(state): return {"messages": [llm.invoke(state["messages"])]}
def route(state): return "tools" if getattr(state["messages"][-1], "tool_calls", None) else "end"
def tools_node(state):
    last = state["messages"][-1]
    return {"messages": [ToolMessage(name="search_documents", content=search_documents.invoke(tc["args"]), tool_call_id=tc["id"]) for tc in last.tool_calls or [] if tc["name"]=="search_documents"]}

graph = StateGraph(State)
graph.add_node("assistant", assistant_node)
graph.add_node("tools", tools_node)
graph.add_edge(START, "assistant")
graph.add_conditional_edges("assistant", route, {"tools": "tools", "end": END})
graph.add_edge("tools", "assistant")
app = graph.compile()

state = {"messages": [SystemMessage(content=SYSTEM_PROMPT)]}
state = app.invoke({"messages": state["messages"] + [HumanMessage(content="Hello!")]})
print(f"Bot: {state['messages'][-1].content}\n")

while True:
    try:
        user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!"); break
    if user_input.lower() == "exit":
        print("Goodbye!"); break
    if not user_input: continue
    state = app.invoke({"messages": state["messages"] + [HumanMessage(content=user_input)]})
    print(f"\nBot: {state['messages'][-1].content}\n")
