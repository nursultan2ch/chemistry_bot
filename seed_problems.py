"""
Script to bulk add problems to the database.
Edit the PROBLEMS list below and run: python seed_problems.py
"""
import database as db

# First, get existing topics or create new ones
# Run this once to see available topics:
# for cat in db.get_all_categories():
#     print(f"\n{cat.name}:")
#     for topic in db.get_topics_by_category(cat.id):
#         print(f"  - {topic.name} (id={topic.id})")

PROBLEMS = [
    # Stoichiometry problems (topic_id=1, adjust if different)
    {
        "topic_id": 1,  # Stoichiometry
        "question": "How many grams of H2O are produced when 4 grams of H2 react with excess O2?\n2H2 + O2 → 2H2O",
        "answer": 36.0,
        "tolerance": 0.5,
        "difficulty": 2,
        "hints": [
            "First find moles of H2",
            "Molar mass of H2 is 2 g/mol",
            "Use stoichiometric ratio 2:2"
        ],
        "steps": [
            "Moles of H2 = 4g ÷ 2g/mol = 2 mol",
            "From equation: 2 mol H2 → 2 mol H2O",
            "Moles of H2O = 2 mol",
            "Mass of H2O = 2 mol × 18 g/mol = 36 g"
        ],
        "common_errors": {
            "18.0": "You calculated for 1 mole of H2O, not 2",
            "72.0": "You doubled when you shouldn't have"
        }
    },
    {
        "topic_id": 1,  # Stoichiometry
        "question": "What mass of NaCl is needed to prepare 500 mL of a 0.5 M solution?",
        "answer": 14.6,
        "tolerance": 0.2,
        "difficulty": 1,
        "hints": [
            "Use the formula: n = M × V",
            "Remember V must be in liters",
            "Molar mass of NaCl = 58.44 g/mol"
        ],
        "steps": [
            "Convert 500 mL to 0.5 L",
            "Moles = 0.5 M × 0.5 L = 0.25 mol",
            "Mass = 0.25 mol × 58.44 g/mol = 14.6 g"
        ],
        "common_errors": {
            "29.2": "You used 500 instead of 0.5 L"
        }
    },
    {
        "topic_id": 2,  # Mole Concept
        "question": "How many molecules are in 0.5 moles of CO2?",
        "answer": 3.01e23,
        "tolerance": 0.1e23,
        "difficulty": 1,
        "hints": [
            "Use Avogadro's number",
            "Avogadro's number = 6.02 × 10²³"
        ],
        "steps": [
            "Number of molecules = moles × Avogadro's number",
            "= 0.5 × 6.02 × 10²³",
            "= 3.01 × 10²³ molecules"
        ],
        "common_errors": {}
    },
    {
        "topic_id": 2,  # Mole Concept
        "question": "What is the molar mass of H2SO4?",
        "answer": 98.0,
        "tolerance": 0.5,
        "difficulty": 1,
        "hints": [
            "H = 1, S = 32, O = 16",
            "Count atoms: 2H + 1S + 4O"
        ],
        "steps": [
            "H: 2 × 1 = 2",
            "S: 1 × 32 = 32",
            "O: 4 × 16 = 64",
            "Total = 2 + 32 + 64 = 98 g/mol"
        ],
        "common_errors": {
            "96.0": "Check your oxygen calculation"
        }
    },
]


def seed_problems():
    """Add all problems to database"""
    added = 0
    for p in PROBLEMS:
        try:
            problem_id = db.create_problem(
                topic_id=p["topic_id"],
                question=p["question"],
                answer=p["answer"],
                tolerance=p.get("tolerance", 0.01),
                difficulty=p.get("difficulty", 1),
                hints=p.get("hints", []),
                steps=p.get("steps", []),
                common_errors=p.get("common_errors", {})
            )
            print(f"✓ Added problem {problem_id}: {p['question'][:50]}...")
            added += 1
        except Exception as e:
            print(f"✗ Error adding problem: {e}")

    print(f"\nAdded {added}/{len(PROBLEMS)} problems")


def list_topics():
    """Show all available topics"""
    print("\nAvailable topics:\n")
    for cat in db.get_all_categories():
        print(f"{cat.icon} {cat.name}:")
        for topic in db.get_topics_by_category(cat.id):
            print(f"    {topic.id}: {topic.icon} {topic.name}")
    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_topics()
    else:
        print("Adding problems to database...\n")
        seed_problems()
