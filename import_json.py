"""
Import problems from a JSON file.
Usage: python import_json.py problems_data.json
"""
import json
import sys
import database as db


def import_from_json(filename):
    with open(filename, 'r') as f:
        data = json.load(f)

    added = 0
    for p in data:
        try:
            # Find topic by name if topic_name is provided
            if "topic_name" in p:
                topic = db.get_topic_by_name(p["topic_name"])
                if not topic:
                    print(f"✗ Topic not found: {p['topic_name']}")
                    continue
                topic_id = topic.id
            else:
                topic_id = p["topic_id"]

            problem_id = db.create_problem(
                topic_id=topic_id,
                question=p["question"],
                answer=p["answer"],
                tolerance=p.get("tolerance", 0.01),
                difficulty=p.get("difficulty", 1),
                hints=p.get("hints", []),
                steps=p.get("steps", []),
                common_errors=p.get("common_errors", {})
            )
            print(f"✓ Added: {p['question'][:50]}...")
            added += 1
        except Exception as e:
            print(f"✗ Error: {e}")

    print(f"\nImported {added} problems")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_json.py <filename.json>")
        print("\nJSON format:")
        print('''[
  {
    "topic_name": "Stoichiometry",
    "question": "Your question here",
    "answer": 42.0,
    "tolerance": 0.1,
    "difficulty": 2,
    "hints": ["Hint 1", "Hint 2"],
    "steps": ["Step 1", "Step 2"],
    "common_errors": {"wrong_answer": "Feedback message"}
  }
]''')
    else:
        import_from_json(sys.argv[1])
