# day5_evaluation_framework.py
import os
from groq import Groq
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ============ TEST CASES ============
test_cases = [
    {
        "name": "RFI_Classification_Accuracy",
        "input": "What is the required concrete strength for the foundation footings? The drawings show 3000 psi but the spec says 4000 psi.",
        "expected_priority": "urgent",
        "expected_trade": "structural",
        "description": "RFI with safety-critical discrepancy should be classified as urgent + structural"
    },
    {
        "name": "RFI_Routing_Correctness",
        "input": "The electrical panel location conflicts with the HVAC ductwork. Can we relocate the panel 2 feet east?",
        "expected_priority": "normal",
        "expected_trade": "mep",
        "description": "MEP-related RFI should route to MEP specialist"
    },
    {
        "name": "RFI_Response_Completeness",
        "input": "The window specification calls for low-E glass but the supplier delivered standard glass. Do we need to replace all windows?",
        "expected_elements": ["design intent", "specification", "replacement", "cost"],
        "description": "Response should address design intent, specs, replacement need, and cost impact"
    },
    {
        "name": "RFI_Code_Citation",
        "input": "What is the required concrete strength for the foundation footings?",
        "expected_codes": ["ACI", "318", "specification"],
        "description": "Structural RFI should cite relevant building codes"
    },
    {
        "name": "RFI_Action_Items",
        "input": "The drawings show 3000 psi but the spec says 4000 psi for foundation footings.",
        "expected_actions": ["revise", "notify", "verify", "confirm"],
        "description": "Response should include specific action items"
    }
]

# ============ LLM HELPER ============
def call_llm(prompt, temp=0.2):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=temp,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

# ============ EVALUATION FUNCTIONS ============
def evaluate_classification(rfi_text, expected_priority, expected_trade):
    """Test if RFI is classified correctly"""
    prompt = f"""Analyze this construction RFI and classify it carefully:

RFI: {rfi_text}

URGENCY RULES:
- urgent = safety issue, structural failure risk, stop-work condition, life safety, code violation
- normal = standard clarification, dimension question, material substitution, coordination issue
- low = aesthetic preference, future consideration, non-critical suggestion

TRADE RULES:
- structural = concrete, steel, foundations, load-bearing, structural integrity
- mep = electrical, plumbing, HVAC, mechanical, fire protection
- architectural = windows, doors, finishes, aesthetics, layout
- general = scheduling, sequencing, general coordination

Respond in EXACTLY this format:
PRIORITY: [urgent/normal/low]
TRADE: [structural/MEP/architectural/general]"""

    result = call_llm(prompt)
    
    priority = "normal"
    trade = "general"
    
    for line in result.split('\n'):
        if 'PRIORITY:' in line:
            priority = line.split(':')[1].strip().lower()
        if 'TRADE:' in line:
            trade = line.split(':')[1].strip().lower()
    
    priority_correct = priority == expected_priority
    trade_correct = trade == expected_trade
    
    return {
        "priority_correct": priority_correct,
        "trade_correct": trade_correct,
        "predicted_priority": priority,
        "predicted_trade": trade,
        "score": (priority_correct + trade_correct) / 2
    }

def evaluate_response_completeness(rfi_text, expected_elements):
    """Test if response contains required elements"""
    prompt = f"""As a construction specialist, draft a response to this RFI:

RFI: {rfi_text}

Your response MUST include:
1. Design intent explanation
2. Specification reference
3. Replacement or action recommendation
4. Cost or schedule impact

Provide a complete, professional response."""

    response = call_llm(prompt)
    
    found_elements = []
    missing_elements = []
    
    for element in expected_elements:
        if element.lower() in response.lower():
            found_elements.append(element)
        else:
            missing_elements.append(element)
    
    score = len(found_elements) / len(expected_elements) if expected_elements else 0
    
    return {
        "found_elements": found_elements,
        "missing_elements": missing_elements,
        "response": response[:200] + "...",
        "score": score
    }

def evaluate_code_citation(rfi_text, expected_codes):
    """Test if response cites relevant codes"""
    prompt = f"""As a structural engineer, respond to this RFI:

RFI: {rfi_text}

Include relevant building codes and standards."""

    response = call_llm(prompt)
    
    found_codes = []
    missing_codes = []
    
    for code in expected_codes:
        if code.lower() in response.lower():
            found_codes.append(code)
        else:
            missing_codes.append(code)
    
    score = len(found_codes) / len(expected_codes) if expected_codes else 0
    
    return {
        "found_codes": found_codes,
        "missing_codes": missing_codes,
        "response": response[:200] + "...",
        "score": score
    }

def evaluate_action_items(rfi_text, expected_actions):
    """Test if response includes action items"""
    prompt = f"""As a project manager, respond to this RFI with clear action items:

RFI: {rfi_text}

Your response MUST include these specific action items:
1. Revise drawings/documents
2. Notify relevant parties
3. Verify compliance
4. Confirm understanding

List actions clearly with responsible parties."""

    response = call_llm(prompt)
    
    found_actions = []
    missing_actions = []
    
    for action in expected_actions:
        if action.lower() in response.lower():
            found_actions.append(action)
        else:
            missing_actions.append(action)
    
    score = len(found_actions) / len(expected_actions) if expected_actions else 0
    
    return {
        "found_actions": found_actions,
        "missing_actions": missing_actions,
        "response": response[:200] + "...",
        "score": score
    }

# ============ RUN EVALUATION ============
def run_evaluation():
    """Run full evaluation suite"""
    print("=" * 60)
    print("🧪 RFI PROCESSOR EVALUATION FRAMEWORK")
    print("=" * 60)
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Total test cases: {len(test_cases)}")
    print("-" * 60)
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📋 TEST {i}/{len(test_cases)}: {test['name']}")
        print(f"   Description: {test['description']}")
        
        if "expected_priority" in test and "expected_trade" in test:
            # Classification test
            result = evaluate_classification(
                test['input'],
                test['expected_priority'],
                test['expected_trade']
            )
            print(f"   Priority: {result['predicted_priority']} (expected: {test['expected_priority']}) {'✅' if result['priority_correct'] else '❌'}")
            print(f"   Trade: {result['predicted_trade']} (expected: {test['expected_trade']}) {'✅' if result['trade_correct'] else '❌'}")
            print(f"   Score: {result['score']:.2f}")
            
        elif "expected_elements" in test:
            # Completeness test
            result = evaluate_response_completeness(
                test['input'],
                test['expected_elements']
            )
            print(f"   Found: {', '.join(result['found_elements'])}")
            print(f"   Missing: {', '.join(result['missing_elements']) if result['missing_elements'] else 'None'}")
            print(f"   Score: {result['score']:.2f}")
            
        elif "expected_codes" in test:
            # Code citation test
            result = evaluate_code_citation(
                test['input'],
                test['expected_codes']
            )
            print(f"   Found codes: {', '.join(result['found_codes'])}")
            print(f"   Missing codes: {', '.join(result['missing_codes']) if result['missing_codes'] else 'None'}")
            print(f"   Score: {result['score']:.2f}")
            
        elif "expected_actions" in test:
            # Action items test
            result = evaluate_action_items(
                test['input'],
                test['expected_actions']
            )
            print(f"   Found actions: {', '.join(result['found_actions'])}")
            print(f"   Missing actions: {', '.join(result['missing_actions']) if result['missing_actions'] else 'None'}")
            print(f"   Score: {result['score']:.2f}")
        
        results.append({
            "test_name": test['name'],
            "score": result['score'],
            "details": result
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 EVALUATION SUMMARY")
    print("=" * 60)
    
    total_score = sum(r['score'] for r in results) / len(results)
    passed = sum(1 for r in results if r['score'] >= 0.8)
    
    print(f"Overall Score: {total_score:.2f} / 1.00")
    print(f"Tests Passed: {passed}/{len(results)} (threshold: 0.80)")
    print(f"Tests Failed: {len(results) - passed}/{len(results)}")
    
    print("\nDetailed Results:")
    for r in results:
        status = "PASS" if r['score'] >= 0.8 else "FAIL"
        print(f"   {r['test_name']}: {r['score']:.2f} [{status}]")
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(test_cases),
        "overall_score": total_score,
        "passed": passed,
        "failed": len(results) - passed,
        "results": results
    }
    
    with open("day5_evaluation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved: day5_evaluation_report.json")
    
    if total_score >= 0.8:
        print("\n✅ SYSTEM READY FOR PRODUCTION")
    else:
        print("\n⚠️ SYSTEM NEEDS IMPROVEMENT")
    
    return report

if __name__ == "__main__":
    run_evaluation()