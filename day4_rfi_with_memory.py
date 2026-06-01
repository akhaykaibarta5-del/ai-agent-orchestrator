# day4_rfi_with_memory.py
import os
import hashlib
from typing import TypedDict
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import chromadb
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ============ MEMORY SETUP ============
chroma_client = chromadb.Client()
rfi_collection = chroma_client.get_or_create_collection("rfi_memory")

def save_rfi_memory(rfi_text, response, trade, priority, feedback=""):
    """Save RFI to vector memory"""
    rfi_id = hashlib.md5(rfi_text.encode()).hexdigest()
    
    rfi_collection.add(
        ids=[rfi_id],
        documents=[rfi_text],
        metadatas=[{
            "response": response,
            "trade": trade,
            "priority": priority,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }]
    )
    print(f"💾 Saved to memory: {rfi_id[:8]}...")

def find_similar_rfi(rfi_text, threshold=0.85):
    """Find similar past RFIs"""
    results = rfi_collection.query(
        query_texts=[rfi_text],
        n_results=1
    )
    
    if results["distances"] and results["distances"][0]:
        distance = results["distances"][0][0]
        similarity = 1 - distance
        
        if similarity > threshold:
            metadata = results["metadatas"][0][0]
            print(f"🧠 Similar RFI found! (similarity: {similarity:.2f})")
            return metadata
    
    return None

def get_memory_stats():
    """Show memory statistics"""
    count = rfi_collection.count()
    print(f"\n📊 MEMORY STATS:")
    print(f"   Total RFIs stored: {count}")
    if count > 0:
        all_data = rfi_collection.get()
        trades = {}
        for meta in all_data["metadatas"]:
            t = meta["trade"]
            trades[t] = trades.get(t, 0) + 1
        print(f"   By trade: {trades}")
    return count

# ============ STATE ============
class RFIState(TypedDict):
    rfi_text: str
    priority: str
    trade: str
    draft_response: str
    approved: bool
    final_response: str
    status: str
    from_memory: bool
    memory_feedback: str

# ============ LLM HELPER ============
def call_llm(prompt, temp=0.3):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=temp,
        max_tokens=800
    )
    return response.choices[0].message.content.strip()

# ============ NODE 1: CHECK MEMORY ============
def check_memory(state: RFIState) -> RFIState:
    """Check if similar RFI exists in memory"""
    print(f"\n🧠 CHECKING MEMORY...")
    
    similar = find_similar_rfi(state["rfi_text"])
    
    if similar:
        print(f"✅ Found similar RFI from {similar['trade']} ({similar['priority']})")
        
        prompt = f"""A similar RFI was previously answered. Use this as reference but adapt for the current RFI:

PAST RESPONSE:
{similar['response']}

CURRENT RFI:
{state['rfi_text']}

Feedback from past: {similar['feedback'] or 'None'}

Draft an improved response."""
        
        draft = call_llm(prompt)
        
        return {
            **state,
            "draft_response": draft,
            "from_memory": True,
            "memory_feedback": similar.get("feedback", ""),
            "trade": similar["trade"],
            "priority": similar["priority"],
            "status": "drafted_from_memory"
        }
    
    print("❌ No similar RFI found. Proceeding with normal flow.")
    return {**state, "from_memory": False, "status": "new_rfi"}

# ============ NODE 2: CLASSIFY ============
def classify_rfi(state: RFIState) -> RFIState:
    """Classify new RFI"""
    if state["from_memory"]:
        return state
    
    print(f"\n📋 CLASSIFYING RFI...")
    
    prompt = f"""Analyze this construction RFI:

RFI: {state['rfi_text']}

Respond in EXACTLY this format:
PRIORITY: [urgent/normal/low]
TRADE: [structural/MEP/architectural/general]"""

    result = call_llm(prompt, temp=0.2)
    
    priority = "normal"
    trade = "general"
    
    for line in result.split('\n'):
        if 'PRIORITY:' in line:
            priority = line.split(':')[1].strip().lower()
        if 'TRADE:' in line:
            trade = line.split(':')[1].strip().lower()
    
    print(f"✅ Priority: {priority} | Trade: {trade}")
    return {**state, "priority": priority, "trade": trade, "status": "classified"}

# ============ NODE 3: ROUTE ============
def route_by_trade(state: RFIState):
    if state["from_memory"]:
        return "general"
    return state.get("trade", "general")

# ============ DRAFT FUNCTIONS ============
def draft_structural(state: RFIState) -> RFIState:
    if state["from_memory"]:
        return state
    print(f"\n🏗️ STRUCTURAL ENGINEER drafting...")
    prompt = f"""As a structural engineer, respond to: {state['rfi_text']}
Priority: {state['priority']}
Be technical, cite codes, include action items."""
    draft = call_llm(prompt)
    return {**state, "draft_response": draft, "status": "drafted"}

def draft_mep(state: RFIState) -> RFIState:
    if state["from_memory"]:
        return state
    print(f"\n⚡ MEP ENGINEER drafting...")
    prompt = f"""As an MEP engineer, respond to: {state['rfi_text']}
Priority: {state['priority']}
Include coordination notes and specs."""
    draft = call_llm(prompt)
    return {**state, "draft_response": draft, "status": "drafted"}

def draft_architectural(state: RFIState) -> RFIState:
    if state["from_memory"]:
        return state
    print(f"\n🏛️ ARCHITECT drafting...")
    prompt = f"""As an architect, respond to: {state['rfi_text']}
Priority: {state['priority']}
Explain design intent, suggest alternatives."""
    draft = call_llm(prompt)
    return {**state, "draft_response": draft, "status": "drafted"}

def draft_general(state: RFIState) -> RFIState:
    if state["from_memory"]:
        return state
    print(f"\n🏗️ GENERAL CONTRACTOR drafting...")
    prompt = f"""As a general contractor, respond to: {state['rfi_text']}
Priority: {state['priority']}
Address schedule and cost implications."""
    draft = call_llm(prompt)
    return {**state, "draft_response": draft, "status": "drafted"}

# ============ HUMAN REVIEW ============
def human_review(state: RFIState) -> RFIState:
    """Review and collect feedback"""
    print(f"\n👤 HUMAN REVIEW")
    print(f"Priority: {state['priority']} | Trade: {state['trade']}")
    if state["from_memory"]:
        print("🧠 This response was adapted from memory")
    print(f"\nDRAFT:\n{state['draft_response'][:300]}...")
    
    if state['priority'] == 'urgent':
        print("\n⚠️ URGENT — Auto-approved")
        return {**state, "approved": True, "status": "approved"}
    
    # Simulated feedback
    feedback = "Include more detail about rebar specifications"
    print(f"\nFeedback: {feedback}")
    
    return {**state, "approved": True, "status": "approved", "feedback": feedback}

# ============ FINALIZE ============
def finalize_response(state: RFIState) -> RFIState:
    """Finalize and save to memory"""
    print(f"\n✅ FINALIZING...")
    
    final = f"""RFI RESPONSE
{'='*50}
Priority: {state['priority'].upper()}
Trade: {state['trade'].upper()}
Status: APPROVED
{'='*50}

{state['draft_response']}

---
Generated by AI Agent System | {'Adapted from memory' if state['from_memory'] else 'New response'}
"""
    
    save_rfi_memory(
        state["rfi_text"],
        state["draft_response"],
        state["trade"],
        state["priority"],
        state.get("feedback", "")
    )
    
    print(f"✅ Final response: {len(final)} chars")
    return {**state, "final_response": final, "status": "completed"}

# ============ BUILD GRAPH ============
from langgraph.graph import StateGraph, END

workflow = StateGraph(RFIState)

workflow.add_node("check_memory", check_memory)
workflow.add_node("classify", classify_rfi)
workflow.add_node("draft_structural", draft_structural)
workflow.add_node("draft_mep", draft_mep)
workflow.add_node("draft_architectural", draft_architectural)
workflow.add_node("draft_general", draft_general)
workflow.add_node("review", human_review)
workflow.add_node("finalize", finalize_response)

workflow.set_entry_point("check_memory")

workflow.add_conditional_edges(
    "check_memory",
    lambda s: "draft" if s["from_memory"] else "classify",
    {"draft": "review", "classify": "classify"}
)

workflow.add_conditional_edges(
    "classify",
    route_by_trade,
    {
        "structural": "draft_structural",
        "mep": "draft_mep",
        "architectural": "draft_architectural",
        "general": "draft_general"
    }
)

for node in ["draft_structural", "draft_mep", "draft_architectural", "draft_general"]:
    workflow.add_edge(node, "review")

workflow.add_edge("review", "finalize")
workflow.add_edge("finalize", END)

app = workflow.compile()

# ============ RUN ============
def process_rfi(rfi_text: str):
    print("=" * 60)
    print("🏗️ RFI PROCESSOR WITH MEMORY")
    print("=" * 60)
    
    get_memory_stats()
    
    initial_state = {
        "rfi_text": rfi_text,
        "priority": "",
        "trade": "",
        "draft_response": "",
        "approved": False,
        "final_response": "",
        "status": "received",
        "from_memory": False,
        "memory_feedback": ""
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print("📋 FINAL OUTPUT")
    print("=" * 60)
    print(result["final_response"])
    
    get_memory_stats()
    return result

# Test: First RFI (new), then similar RFI (from memory)
test_rfis = [
    "What is the required concrete strength for the foundation footings? The drawings show 3000 psi but the spec says 4000 psi.",
    "The foundation footing concrete strength is unclear. Drawings say 3000 psi but specifications require 4000 psi. Which is correct?"
]

if __name__ == "__main__":
    print("RFI 1 (NEW - will be stored in memory):")
    process_rfi(test_rfis[0])
    
    print("\n" + "="*60)
    print("RFI 2 (SIMILAR - should use memory):")
    process_rfi(test_rfis[1])