# day2_multi_agent_pipeline.py
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_llm(prompt, temperature=0.5):
    """Helper to call Groq LLM"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=1000
    )
    return response.choices[0].message.content

# ============ AGENT 1: RESEARCHER ============
def researcher_agent(topic: str) -> dict:
    """Gathers key points about a topic"""
    print(f"\n🔍 RESEARCHER: Researching '{topic}'...")
    
    prompt = f"""Research the topic '{topic}'. 
    Provide 5 key facts or insights that would be useful for writing a blog post.
    Format as bullet points. Be concise but informative."""
    
    research = call_llm(prompt)
    
    print(f"✅ Research complete: {len(research)} characters")
    return {"research": research, "topic": topic}

# ============ AGENT 2: WRITER ============
def writer_agent(state: dict) -> dict:
    """Writes blog post using research"""
    print(f"\n✍️  WRITER: Writing blog post...")
    
    prompt = f"""Write a 300-word blog post about '{state['topic']}'.
    
    Use this research:
    {state['research']}
    
    Make it engaging, informative, and well-structured.
    Include a catchy title and conclusion."""
    
    draft = call_llm(prompt)
    
    print(f"✅ Draft complete: {len(draft)} characters")
    return {"draft": draft}

# ============ AGENT 3: EDITOR ============
def editor_agent(state: dict) -> dict:
    """Reviews and improves the draft"""
    print(f"\n📝 EDITOR: Reviewing draft...")
    
    prompt = f"""Review this blog post and improve it:
    
    {state['draft']}
    
    Fix any grammar issues, improve flow, and make it more engaging.
    Return the improved version with a brief note about what you changed."""
    
    final = call_llm(prompt)
    
    print(f"✅ Final version complete: {len(final)} characters")
    return {"final": final}

# ============ ORCHESTRATION PIPELINE ============
def run_pipeline(topic: str):
    """Run the full 3-agent pipeline"""
    print("=" * 60)
    print("🤖 MULTI-AGENT CONTENT PIPELINE")
    print("=" * 60)
    print(f"Topic: {topic}")
    print("-" * 60)
    
    # Step 1: Research
    state = researcher_agent(topic)
    
    # Step 2: Write
    state = writer_agent(state)
    
    # Step 3: Edit
    state = editor_agent(state)
    
    print("\n" + "=" * 60)
    print("🎉 FINAL OUTPUT")
    print("=" * 60)
    print(state["final"])
    print("=" * 60)
    
    return state

# ============ RUN IT ============
if __name__ == "__main__":
    topic = input("Enter a topic for the blog post: ")
    result = run_pipeline(topic)