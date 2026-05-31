# day3_langgraph_rfi_processor.py
import os
from typing import TypedDict, Literal
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ============ STATE DEFINITION ============
class RFIState(TypedDict):
    rfi_text: str
    priority: str
    trade: str
    draft_response: str
    approved: bool
    final_response: str
    status: str

# ============ LLM HELPER ============
def call_llm(prompt, temp=0.3):
    """Call Groq with lower temp for business consistency"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=temp,
        max_tokens=800
    )
    return response.choices[0].message.content.strip()

# ============ NODE 1: PARSE & CLASSIFY ============
def classify_rfi(state: RFIState) -> RFIState:
    """Parse RFI and determine priority + trade"""
    print(f"\n📋 CLASSIFYING RFI...")
    
    prompt = f"""Analyze this construction RFI and classify it:

RFI: {state['rfi_text']}

Respond in EXACTLY this format:
PRIORITY: [urgent/normal/low]
TRADE: [structural/MEP/architectural/general]

Rules:
- urgent = safety issue, structural concern, stop-work condition
- normal = standard clarification, dimension question
- low = aesthetic preference, future consideration"""

    result = call_llm(prompt, temp=0.2)
    
    # Parse the response
    priority = "normal"
    trade = "general"
    
    for line in result.split('\n'):
        if 'PRIORITY:' in line:
            priority = line.split(':')[1].strip().lower()
        if 'TRADE:' in line:
            trade = line.split(':')[1].strip().lower()
    
    print(f"✅ Priority: {priority} | Trade: {trade}")
    
    return {
        **state,
        "priority": priority,
        "trade": trade,
        "status": "classified"
    }

# ============ NODE 2: ROUTE BY TRADE ============
def route_by_trade(state: RFIState) -> Literal["structural", "mep", "architectural", "general"]:
    """Determine which specialist handles this RFI"""
    trade_map = {
        "structural": "structural",
        "mep": "mep", 
        "architectural": "architectural"
    }
    return trade_map.get(state["trade"], "general")

# ============ NODE 3: DRAFT RESPONSES ============
def draft_structural(state: RFIState) -> RFIState:
    """Structural engineer drafts response"""
    print(f"\n🏗️  STRUCTURAL ENGINEER drafting response...")
    
    prompt = f"""As a structural engineer, draft a response to this RFI:

RFI: {state['rfi_text']}
Priority: {state['priority']}

Provide a technical but clear response. Include:
- Direct answer to the question
- Reference to relevant codes/standards if applicable
- Any action items or clarifications needed

Keep it professional and concise."""

    draft = call_llm(prompt)
    print(f"✅ Draft complete: {len(draft)} chars")
    
    return {**state, "draft_response": draft, "status": "drafted"}

def draft_mep(state: RFIState) -> RFIState:
    """MEP engineer drafts response"""
    print(f"\n⚡ MEP ENGINEER drafting response...")
    
    prompt = f"""As an MEP (Mechanical/Electrical/Plumbing) engineer, draft a response to this RFI:

RFI: {state['rfi_text']}
Priority: {state['priority']}

Provide a technical but clear response. Include:
- Direct answer to the question
- Coordination notes with other trades if relevant
- Any specifications or standards to reference

Keep it professional and concise."""

    draft = call_llm(prompt)
    print(f"✅ Draft complete: {len(draft)} chars")
    
    return {**state, "draft_response": draft, "status": "drafted"}

def draft_architectural(state: RFIState) -> RFIState:
    """Architect drafts response"""
    print(f"\n🏛️ ARCHITECT drafting response...")
    
    prompt = f"""As an architect, draft a response to this RFI:

RFI: {state['rfi_text']}
Priority: {state['priority']}

Provide a clear response. Include:
- Design intent explanation
- Alternative solutions if applicable
- Any drawings or details that need updating

Keep it professional and concise."""

    draft = call_llm(prompt)
    print(f"✅ Draft complete: {len(draft)} chars")
    
    return {**state, "draft_response": draft, "status": "drafted"}

def draft_general(state: RFIState) -> RFIState:
    """General contractor drafts response"""
    print(f"\n🏗️ GENERAL CONTRACTOR drafting response...")
    
    prompt = f"""As a general contractor, draft a response to this RFI:

RFI: {state['rfi_text']}
Priority: {state['priority']}

Provide a practical response. Include:
- Direct answer based on contract documents
- Schedule impact if any
- Cost implications if any

Keep it professional and concise."""

    draft = call_llm(prompt)
    print(f"✅ Draft complete: {len(draft)} chars")
    
    return {**state, "draft_response": draft, "status": "drafted"}

# ============ NODE 4: HUMAN REVIEW (SIMULATED) ============
def human_review(state: RFIState) -> RFIState:
    """Simulate human approval process"""
    print(f"\n👤 HUMAN REVIEW REQUIRED")
    print(f"Priority: {state['priority']} | Trade: {state['trade']}")
    print(f"\nDRAFT RESPONSE:\n{state['draft_response'][:200]}...")
    
    # For demo: auto-approve urgent, ask for normal/low
    if state['priority'] == 'urgent':
        print("\n⚠️ URGENT RFI — Auto-approved for speed (in production, this would notify manager)")
        return {**state, "approved": True, "status": "approved"}
    
    # Simulate human decision
    print(f"\n{'='*60}")
    print("APPROVE this response? (y/n): ", end="")
    # For demo, auto-approve
    decision = "y"
    print(decision)
    
    if decision.lower() == 'y':
        return {**state, "approved": True, "status": "approved"}
    else:
        return {**state, "approved": False, "status": "rejected"}

# ============ NODE 5: FINALIZE ============
def finalize_response(state: RFIState) -> RFIState:
    """Finalize approved response"""
    print(f"\n✅ FINALIZING RESPONSE...")
    
    final = f"""RFI RESPONSE
{'='*50}
Priority: {state['priority'].upper()}
Trade: {state['trade'].upper()}
Status: APPROVED

RESPONSE:
{state['draft_response']}

---
Generated by AI Agent System | Reviewed by Human
"""
    
    print(f"✅ Final response ready: {len(final)} chars")
    return {**state, "final_response": final, "status": "completed"}

# ============ BUILD THE GRAPH ============
from langgraph.graph import StateGraph, END

# Create graph
workflow = StateGraph(RFIState)

# Add nodes
workflow.add_node("classify", classify_rfi)
workflow.add_node("draft_structural", draft_structural)
workflow.add_node("draft_mep", draft_mep)
workflow.add_node("draft_architectural", draft_architectural)
workflow.add_node("draft_general", draft_general)
workflow.add_node("review", human_review)
workflow.add_node("finalize", finalize_response)

# Add edges
workflow.set_entry_point("classify")

# Conditional routing after classification
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

# All drafts go to review
workflow.add_edge("draft_structural", "review")
workflow.add_edge("draft_mep", "review")
workflow.add_edge("draft_architectural", "review")
workflow.add_edge("draft_general", "review")

# Review goes to finalize
workflow.add_edge("review", "finalize")

# End
workflow.add_edge("finalize", END)

# Compile
app = workflow.compile()

# ============ RUN IT ============
def process_rfi(rfi_text: str):
    """Process an RFI through the full pipeline"""
    print("=" * 60)
    print("🏗️ CONSTRUCTION RFI PROCESSOR")
    print("=" * 60)
    
    initial_state = {
        "rfi_text": rfi_text,
        "priority": "",
        "trade": "",
        "draft_response": "",
        "approved": False,
        "final_response": "",
        "status": "received"
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print("📋 FINAL OUTPUT")
    print("=" * 60)
    print(result["final_response"])
    
    return result

# Test RFIs
test_rfis = [
    "What is the required concrete strength for the foundation footings? The drawings show 3000 psi but the spec says 4000 psi.",
    "The electrical panel location conflicts with the HVAC ductwork. Can we relocate the panel 2 feet east?",
    "The window specification calls for low-E glass but the supplier delivered standard glass. Do we need to replace all windows?"
]

if __name__ == "__main__":
    print("Choose an RFI to process:")
    for i, rfi in enumerate(test_rfis, 1):
        print(f"{i}. {rfi[:60]}...")
    
    choice = input("\nEnter number (1-3) or type your own RFI: ")
    
    if choice in ["1", "2", "3"]:
        rfi = test_rfis[int(choice) - 1]
    else:
        rfi = choice
    
    process_rfi(rfi)