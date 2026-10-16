
from src.orchestrator import run_system

question = (
    "Should I register a company, estimate my budget, "
    "and understand GST?"
)

result = run_system(question)

print("\n=== MULTI-MODEL SYSTEM ===")
print("Selected experts:", result["selected_experts"])

print("\n=== FINAL SYNTHESIZED ANSWER ===")
print(result["synthesis"]["final_answer"])

print("\nExpert count:", result["synthesis"]["expert_count"])
