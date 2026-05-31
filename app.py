import gradio as gr

def calculate_cost(num_agents, avg_turns, input_tokens, output_tokens, executions_per_day):
    executions_per_month = executions_per_day * 30
    
    pricing = {
        "Groq (Free Tier)": {"input": 0.00, "output": 0.00},
        "Ollama (Local)": {"input": 0.00, "output": 0.00},
        "OpenAI GPT-4o-mini": {"input": 0.15, "output": 0.60},
        "OpenAI GPT-4o": {"input": 2.50, "output": 10.00},
        "Claude 3.5 Haiku": {"input": 0.25, "output": 1.25},
    }
    
    results = []
    for model_name, prices in pricing.items():
        input_cost = (input_tokens * num_agents * avg_turns * executions_per_month / 1_000_000) * prices["input"]
        output_cost = (output_tokens * num_agents * avg_turns * executions_per_month / 1_000_000) * prices["output"]
        total = input_cost + output_cost
        
        if total == 0:
            results.append(f"✅ {model_name}: $0.00/month (FREE)")
        else:
            results.append(f"💰 {model_name}: ${total:.2f}/month")
    
    return "\n".join(results)

demo = gr.Interface(
    fn=calculate_cost,
    inputs=[
        gr.Number(label="Number of agents", value=3),
        gr.Number(label="Avg turns per agent", value=3),
        gr.Number(label="Input tokens per turn", value=500),
        gr.Number(label="Output tokens per turn", value=300),
        gr.Number(label="Executions per day", value=100),
    ],
    outputs=gr.Textbox(label="Monthly Cost Comparison", lines=8),
    title="🤖 AI Agent Cost Calculator",
    description="Calculate exactly what your multi-agent system will cost — $0 to start with free tiers!",
)

demo.launch()