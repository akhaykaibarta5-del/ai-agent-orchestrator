import streamlit as st

st.set_page_config(page_title="AI Agent Cost Calculator", page_icon="🤖")

st.title("🤖 AI Agent Cost Calculator")
st.write("Calculate exactly what your multi-agent system will cost — **$0 to start**")

pricing = {
    "🆓 Groq (Free Tier)": {"input": 0.00, "output": 0.00, "note": "1M tokens/day free"},
    "🆓 Ollama (Local)": {"input": 0.00, "output": 0.00, "note": "Run on your hardware"},
    "💰 OpenAI GPT-4o-mini": {"input": 0.15, "output": 0.60, "note": "Paid API"},
    "💰 OpenAI GPT-4o": {"input": 2.50, "output": 10.00, "note": "Paid API"},
    "💰 Claude 3.5 Haiku": {"input": 0.25, "output": 1.25, "note": "Paid API"},
}

st.subheader("Your Agent Configuration")
col1, col2 = st.columns(2)

with col1:
    num_agents = st.number_input("Number of agents", 1, 20, 3)
    avg_turns = st.number_input("Avg turns per agent", 1, 50, 3)

with col2:
    input_tokens = st.number_input("Input tokens per turn", 100, 10000, 500)
    output_tokens = st.number_input("Output tokens per turn", 100, 10000, 300)

executions_per_day = st.number_input("Executions per day", 1, 100000, 100)
executions_per_month = executions_per_day * 30

st.subheader("💰 Monthly Cost Comparison")

for model_name, prices in pricing.items():
    input_cost = (input_tokens * num_agents * avg_turns * executions_per_month / 1_000_000) * prices["input"]
    output_cost = (output_tokens * num_agents * avg_turns * executions_per_month / 1_000_000) * prices["output"]
    total = input_cost + output_cost
    
    if total == 0:
        st.success(f"**{model_name}**: $0.00/month ✅")
    else:
        st.warning(f"**{model_name}**: ${total:.2f}/month")
    
    st.caption(f"  {prices['note']}")

st.subheader("🎯 The Zero-Budget Strategy")
st.info("""
1. **Build with Groq (free)** — 1M tokens/day is enough for development + demos
2. **Test with Ollama (local)** — Run Llama 3.1 on your laptop for unlimited testing  
3. **Deploy with Hugging Face Spaces (free)** — Host your app without paying for servers
4. **Only pay for APIs when a CLIENT pays you** — Never spend your own money
""")