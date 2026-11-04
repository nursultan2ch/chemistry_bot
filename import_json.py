"""
Import problems from a JSON file. Problems already in the database are skipped.
Usage: python import_json.py [path/to/problems.json]   (default: data/problems.json)
"""
import sys
import database as db


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else db.PROBLEMS_FILE
    db.seed_initial_data()
    added, skipped = db.import_problems(path)
    print(f"Imported {added} problems ({skipped} skipped)")
