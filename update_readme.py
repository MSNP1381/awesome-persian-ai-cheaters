import json

def update_readme(violator_url, similarity):
    with open('README.md', 'a') as f:
        f.write(f"\n- [Violating Channel]({violator_url}) - Similarity: {similarity:.2f}")

def main():
    with open('violation_detected', 'r') as f:
        data = json.load(f)
    
    update_readme(data['violator_url'], data['similarity'])

if __name__ == "__main__":
    main()