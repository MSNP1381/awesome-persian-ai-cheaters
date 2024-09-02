import json
import sys

def update_readme(violator_url, similarity):
    try:
        with open('README.md', 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(f"- [Violating Channel]({violator_url}) - Similarity: {similarity:.2f}\n{content}")
        print(f"Successfully added new violator: {violator_url}")
    except IOError as e:
        print(f"Error updating README.md: {str(e)}", file=sys.stderr)
        raise

def main():
    try:
        with open('violation_detected', 'r') as f:
            data = json.load(f)
        
        update_readme(data['violator_url'], data['similarity'])
        return 0
    except Exception as e:
        print(f"An error occurred: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    main()