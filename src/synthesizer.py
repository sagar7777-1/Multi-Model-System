
def synthesize_answer(
    question: str,
    expert_answers: dict[str, str],
) -> dict:
    """
    Combine expert responses into one structured answer.
    This is a baseline synthesizer, not an LLM.
    """

    # Collect the available expert responses
    sections = []

    for expert_name, answer in expert_answers.items():
        sections.append({
            "expert": expert_name,
            "findings": answer,
        })

    # Build a single response
    final_answer = (
        f"Question: {question}\n\n"
        "Expert review:\n"
    )

    for section in sections:
        final_answer += (
            f"\n{section['expert'].upper()}:\n"
            f"{section['findings']}\n"
        )

    return {
        "question": question,
        "expert_count": len(sections),
        "expert_sections": sections,
        "final_answer": final_answer,
    }
