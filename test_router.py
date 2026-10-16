
from src.router import route_question

question = (
    "Should I register a company, estimate my budget, "
    "and understand GST?"
)

experts = route_question(question)

print("Question:", question)
print("Selected experts:", experts)

assert experts == ["legal", "finance", "tax"]

print("Router test passed!")
