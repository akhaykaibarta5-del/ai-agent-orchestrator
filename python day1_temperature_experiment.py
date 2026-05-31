# day1_temperature_experiment.py
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

prompt = "Explain why multi-agent orchestration is harder than building a single chatbot, in exactly 3 sentences."

print("=" * 60)
print("AI AGENT ORCHESTRATION - TEMPERATURE EXPERIMENT")
print("=" * 60)

for temp in [0.0, 0.5, 1.0]:
    print(f"\n🌡️  TEMPERATURE: {temp}")
    print("-" * 40)
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # FREE on Groq
        messages=[{"role": "user", "content": prompt}],
        temperature=temp,
        max_tokens=150
    )
    
    output = response.choices[0].message.content
    tokens = response.usage.total_tokens
    
    print(f"Output: {output}")
    print(f"Tokens used: {tokens}")
    print("-" * 40)

print("\n✅ Experiment complete!")
print("💡 Insight: Lower temperature = more deterministic. Higher = more creative.")