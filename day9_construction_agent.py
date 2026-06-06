#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
import re
import os
import json
import math
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# Force UTF-8 output for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ============ TOOL 1: WEB SEARCH ============
def web_search(query: str, num_results: int = 3) -> str:
    """Search the web for construction codes, regulations, general info"""
    try:
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        snippets = []
        for line in response.text.split('class="result__snippet"'):
            if '>' in line and '<' in line:
                text = line.split('>')[1].split('<')[0]
                if len(text) > 20:
                    snippets.append(text.strip())
        
        results = snippets[:num_results]
        return json.dumps({
            "query": query,
            "results": results,
            "count": len(results),
            "source": "web_search"
        })
    except Exception as e:
        return json.dumps({"error": str(e), "query": query, "source": "web_search"})

# ============ TOOL 2: CALCULATOR ============
def calculator(expression: str) -> str:
    """Construction math: volumes, costs, quantities"""
    try:
        expression = expression.replace('^', '**')
        
        allowed_names = {
            "sqrt": math.sqrt, "pow": math.pow, "abs": abs,
            "round": round, "max": max, "min": min,
            "sum": sum, "pi": math.pi
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        
        return json.dumps({
            "expression": expression,
            "result": result,
            "status": "success",
            "source": "calculator"
        })
    except Exception as e:
        return json.dumps({
            "expression": expression,
            "error": str(e),
            "status": "failed",
            "source": "calculator"
        })

# ============ TOOL 3: EMAIL NOTIFICATION (REAL SMTP) ============
def send_notification(to: str, subject: str, body: str) -> str:
    """Send real email via Gmail SMTP"""
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        
        if not smtp_username or not smtp_password:
            print("⚠️ No SMTP configured, falling back to log only")
            return _log_notification(to, subject, body)
        
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = to
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        print(f"📧 Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        print(f"📧 Logging in as {smtp_username}...")
        server.login(smtp_username, smtp_password)
        
        print(f"📧 Sending email to {to}...")
        server.sendmail(smtp_username, to, msg.as_string())
        server.quit()
        
        print(f"✅ Email sent successfully to {to}")
        
        _log_notification(to, subject, body, status="sent_via_email")
        
        return json.dumps({
            "status": "success",
            "message": f"Email sent to {to}",
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
            "source": "notification",
            "method": "smtp"
        })
        
    except Exception as e:
        print(f"❌ Email failed: {str(e)}")
        print(f"⚠️ Falling back to log only")
        return _log_notification(to, subject, body, error=str(e))

def _log_notification(to: str, subject: str, body: str, status="logged", error=None) -> str:
    """Log notification to file as fallback"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notification = {
        "to": to,
        "subject": subject,
        "body_preview": body[:150] + "..." if len(body) > 150 else body,
        "status": status,
        "timestamp": timestamp,
        "error": error,
        "source": "notification"
    }
    
    with open("notifications_log.jsonl", "a") as f:
        f.write(json.dumps(notification) + "\n")
    
    return json.dumps({
        "status": status,
        "message": f"Notification logged for {to}" + (f" (Error: {error})" if error else ""),
        "subject": subject,
        "timestamp": timestamp,
        "source": "notification"
    })

# ============ TOOL 4: PRICE LOOKUP (LLM Knowledge) ============
def get_market_price(item: str, location: str = "India") -> str:
    """Get approximate market price using LLM knowledge"""
    try:
        prompt = f"""What is the approximate current market price (in INR/₹) for {item} in {location} as of 2026?

Respond ONLY with a JSON object in this exact format:
{{
    "item": "{item}",
    "price_per_unit": 4500,
    "unit": "cubic meter",
    "currency": "INR",
    "location": "{location}",
    "price_range_low": 4000,
    "price_range_high": 5000,
    "source": "LLM knowledge - approximate market rate",
    "note": "Prices vary by region, supplier, and market conditions. Contact local suppliers for exact quotes."
}}

If you don't know the exact price, provide your best estimate based on general construction industry knowledge."""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        price_data = json.loads(content)
        
        return json.dumps({
            "status": "success",
            "price_data": price_data,
            "source": "price_lookup"
        })
        
    except Exception as e:
        return json.dumps({
            "status": "fallback",
            "price_data": {
                "item": item,
                "price_per_unit": 4500,
                "unit": "cubic meter",
                "currency": "INR",
                "location": location,
                "note": "Default approximate price. Contact suppliers for exact quotes."
            },
            "error": str(e),
            "source": "price_lookup"
        })

# ============ CONSTRUCTION AGENT ============
class ConstructionAgent:
    def __init__(self):
        self.client = client
        self.tools = {
            "web_search": web_search,
            "calculator": calculator,
            "send_notification": send_notification,
            "get_market_price": get_market_price
        }
        self.session_log = []
    
    def analyze_needs(self, user_input: str) -> dict:
        """Step 1: Analyze what tools are needed"""
        
        analysis_prompt = f"""Analyze this construction request and decide which tools to use.

Request: "{user_input}"

Available tools:
- web_search: Find building codes, regulations, technical specifications online
- calculator: Solve math, calculate volumes, costs, quantities
- get_market_price: Get approximate market prices using industry knowledge (INR/₹)
- send_notification: Email results to stakeholders

IMPORTANT INSTRUCTIONS:
1. For price queries, use get_market_price instead of web_search
2. For calculator, ALWAYS provide a calculation expression with actual numbers
3. Use ** for exponentiation (NOT ^)
4. Example: "4500 * 50" for cost calculation
5. Example: "3.14159 * (0.008)**2 * 100" for cylinder volume

Respond ONLY in this JSON format (no other text):
{{
    "needs_search": true/false,
    "search_query": "specific search query if needed, else empty string",
    "needs_price_lookup": true/false,
    "price_item": "item name for price lookup, else empty string",
    "price_location": "location for price, default India, else empty string",
    "needs_calculator": true/false,
    "calculation_expression": "math expression with actual numbers using ** for powers, else empty string",
    "needs_notification": true/false,
    "notification_email": "email if needed, else empty string",
    "notification_subject": "subject line if needed, else empty string",
    "reasoning": "brief explanation of why these tools were chosen"
}}"""

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        analysis_text = response.choices[0].message.content.strip()
        
        if "```json" in analysis_text:
            analysis_text = analysis_text.split("```json")[1].split("```")[0].strip()
        elif "```" in analysis_text:
            analysis_text = analysis_text.split("```")[1].split("```")[0].strip()
        
        try:
            return json.loads(analysis_text)
        except:
            return {
                "needs_search": False,
                "search_query": "",
                "needs_price_lookup": False,
                "price_item": "",
                "price_location": "",
                "needs_calculator": False,
                "calculation_expression": "",
                "needs_notification": False,
                "notification_email": "",
                "notification_subject": "",
                "reasoning": "Failed to parse analysis"
            }
    
    def process(self, user_input: str, notify_email: str = None) -> dict:
        """Main processing pipeline"""
        start_time = datetime.now()
        
        print(f"\n🔍 Analyzing: {user_input[:60]}...")
        
        # Step 1: Analyze needs
        analysis = self.analyze_needs(user_input)
        print(f"🧠 Analysis: {analysis['reasoning']}")
        print(f"🔍 DEBUG: Raw calculation expression: '{analysis.get('calculation_expression', '')}'")
        
        # Step 2: Execute tools
        tool_results = []
        extracted_price = None
        
        # Price lookup first (if needed)
        if analysis.get("needs_price_lookup") and analysis.get("price_item"):
            print(f"🔧 Tool: get_market_price('{analysis['price_item']}', '{analysis.get('price_location', 'India')}')")
            result = get_market_price(analysis["price_item"], analysis.get("price_location", "India"))
            parsed_result = json.loads(result)
            tool_results.append({"tool": "get_market_price", "result": parsed_result})
            
            if parsed_result.get("status") == "success":
                price_data = parsed_result.get("price_data", {})
                extracted_price = price_data.get("price_per_unit")
                print(f"✅ Price lookup complete: ₹{extracted_price:,.2f} per {price_data.get('unit', 'unit')}")
                print(f"📊 Price range: ₹{price_data.get('price_range_low', 'N/A')} - ₹{price_data.get('price_range_high', 'N/A')}")
            else:
                print(f"⚠️ Price lookup failed, using fallback")
                extracted_price = 4500
        
        # Web search (for codes, regulations, NOT prices)
        if analysis.get("needs_search") and analysis.get("search_query"):
            print(f"🔧 Tool: web_search('{analysis['search_query']}')")
            result = web_search(analysis["search_query"])
            parsed_result = json.loads(result)
            tool_results.append({"tool": "web_search", "result": parsed_result})
            print(f"✅ Search complete: {len(parsed_result.get('results', []))} results")
        
        # Calculator
        calc_expression = analysis.get("calculation_expression", "")
        print(f"🔍 DEBUG: Original calc expression: '{calc_expression}'")
        
        # FIX: Initialize variables before the if block
        variables = []
        
        # If price was looked up, inject it into calculation
        if extracted_price and calc_expression:
            math_functions = {'sqrt', 'pow', 'abs', 'round', 'max', 'min', 'sum', 'pi'}
            
            operators = r'[\+\-\*/\(\)\,\.\*\*]'
            parts = re.split(operators, calc_expression)
            variables = []
            for part in parts:
                part = part.strip()
                if part and not part.replace('.', '').isdigit() and part not in math_functions:
                    variables.append(part)
            
            print(f"🔍 DEBUG: Detected variables: {variables}")
            
            if variables:
                for var in variables:
                    calc_expression = re.sub(r'\b' + re.escape(var) + r'\b', str(extracted_price), calc_expression)
                print(f"🔄 Replaced variables with price ₹{extracted_price}: {calc_expression}")
        
        print(f"🔍 DEBUG: Final calc expression before calculator: '{calc_expression}'")
        
        if analysis.get("needs_calculator") and calc_expression:
            print(f"🔧 Tool: calculator('{calc_expression}')")
            result = calculator(calc_expression)
            tool_results.append({"tool": "calculator", "result": json.loads(result)})
            calc_result = tool_results[-1]['result'].get('result', 'N/A')
            print(f"✅ Calculation complete: {calc_result}")
        
        # Step 3: Generate final answer
        print("📝 Generating final answer...")
        
        price_context = ""
        if extracted_price:
            price_context = f"\nExtracted Price from Search: ₹{extracted_price:,.2f} per cubic meter"
        elif variables and not extracted_price:
            price_context = f"\nNote: Used approximate market price of ₹4,500 per cubic meter (search results were unclear)"
        
        context = f"""Tool Results:
{json.dumps(tool_results, indent=2)}
{price_context}

Original Request: {user_input}"""

        final_prompt = f"""You are a Construction Research Assistant. Answer this request using the tool results provided.

{context}

Provide a clear, professional answer with:
- Key findings from research
- Calculations shown step-by-step
- Price information with source and range
- Practical recommendations
- Safety warnings if applicable
- Note that prices are approximate and may vary by region/supplier

Answer:"""

        final_response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.2,
            max_tokens=1500
        )
        
        final_answer = final_response.choices[0].message.content
        
        # Step 4: Send notification if requested
        notification_info = None
        if notify_email or (analysis.get("needs_notification") and analysis.get("notification_email")):
            email = notify_email or analysis["notification_email"]
            subject = analysis.get("notification_subject", f"Construction Report: {user_input[:50]}...")
            
            print(f"📧 Sending notification to {email}...")
            notification_body = f"""Construction Agent Report

Query: {user_input}

Findings:
{final_answer[:800]}

---
Generated by AI Construction Agent
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            notification_result = send_notification(
                to=email,
                subject=subject,
                body=notification_body
            )
            notification_info = json.loads(notification_result)
            print(f"✅ Notification: {notification_info['message']}")
        
        # Prepare result
        elapsed = (datetime.now() - start_time).total_seconds()
        
        result = {
            "query": user_input,
            "answer": final_answer,
            "tools_used": [t["tool"] for t in tool_results],
            "tool_details": tool_results,
            "analysis": analysis,
            "extracted_price": extracted_price,
            "processing_time_seconds": round(elapsed, 2),
            "timestamp": datetime.now().isoformat(),
            "notification": notification_info
        }
        
        self.session_log.append(result)
        
        print(f"✅ Complete in {elapsed:.1f}s | Tools: {', '.join(result['tools_used']) or 'None'}")
        
        return result
    
    def get_session_summary(self) -> dict:
        """Get summary of all queries"""
        return {
            "total_queries": len(self.session_log),
            "tools_used_total": sum(len(q["tools_used"]) for q in self.session_log),
            "avg_processing_time": sum(q["processing_time_seconds"] for q in self.session_log) / max(len(self.session_log), 1),
            "queries": [q["query"] for q in self.session_log]
        }

# ============ DEMO ============
if __name__ == "__main__":
    print("🏗️ Construction Research & Notification Agent")
    print("=" * 60)
    print("LLM Price Lookup | Web Search for Codes | Calculator | Real Email Notifications")
    print("=" * 60)
    
    agent = ConstructionAgent()
    
    # Demo 1: Price Lookup + Calculate + Send REAL Email
    print("\n📋 DEMO 1: Foundation Cost Estimate")
    print("-" * 50)
    result = agent.process(
        "What is the current price of M25 concrete per cubic meter in India? Calculate cost for 50 cubic meters.",
        notify_email="akhaykaibarta5@gmail.com"
    )
    
    print(f"\n📊 Answer Preview:\n{result['answer'][:400]}...")
    if result.get('extracted_price'):
        print(f"\n💰 Extracted Price: ₹{result['extracted_price']:,.2f} per cubic meter")
    
    # Demo 2: Code Research (web search)
    print("\n\n📋 DEMO 2: Building Code Research")
    print("-" * 50)
    result = agent.process(
        "What is the minimum reinforcement requirement for RCC beams as per IS 456:2000?"
    )
    
    print(f"\n📊 Answer Preview:\n{result['answer'][:400]}...")
    
    # Demo 3: Steel Weight Calculation (calculator only)
    print("\n\n📋 DEMO 3: Steel Weight Calculation")
    print("-" * 50)
    result = agent.process(
        "Calculate the weight of 100 meters of 16mm diameter steel bar. Density is 7850 kg/m3. Formula: weight = density * pi * (diameter/2/1000)**2 * length"
    )
    
    print(f"\n📊 Answer Preview:\n{result['answer'][:400]}...")
    
    # Session Summary
    print("\n\n📊 SESSION SUMMARY")
    print("-" * 50)
    summary = agent.get_session_summary()
    print(f"Total queries: {summary['total_queries']}")
    print(f"Total tool calls: {summary['tools_used_total']}")
    print(f"Avg time: {summary['avg_processing_time']:.2f}s")