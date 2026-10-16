
from src.router import route_question
from src.synthesizer import synthesize_answer
from src.experts import (
    legal_expert,
    finance_expert,
    tax_expert,
)


# Map expert names to their functions

EXPERTS = {
    "legal": legal_expert,
    "finance": finance_expert,
    "tax": tax_expert,
}

# Reuse the experts selected by your existing router.
expert_results = {}

for expert_name in selected_experts:
    expert_function = EXPERTS.get(expert_name)

    if expert_function:
        try:
            expert_results[expert_name] = expert_function(question)
        except (requests.RequestException, KeyError, ValueError) as exc:
            expert_results[expert_name] = (
                f"Expert failed: {type(exc).__name__}: {exc}"
            )

print("\n=== REAL EXPERT RESULTS ===")
for name, result in expert_results.items():
    print(f"\n{name.upper()}:\n{result}")
