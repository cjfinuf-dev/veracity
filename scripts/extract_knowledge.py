"""One-time script to extract VERA_KNOWLEDGE from index.html into vera-knowledge.json."""
import re, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'index.html')
OUT  = os.path.join(ROOT, 'data', 'vera-knowledge.json')

with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# Extract the VERA_KNOWLEDGE array block
m = re.search(r'const VERA_KNOWLEDGE = \[(.*?)\];', html, re.DOTALL)
if not m:
    raise RuntimeError('Could not find VERA_KNOWLEDGE in index.html')

block = m.group(1)

# Parse each entry object using regex (JS object literals)
entries = []
# Match each { patterns: [...], response: '...', action: ... } block
pattern = re.compile(
    r"\{\s*patterns:\s*\[([^\]]+)\]\s*,\s*response:\s*(['\"])(.*?)\2\s*"
    r"(?:,\s*action:\s*(\{[^}]+\}))?\s*\}",
    re.DOTALL
)

for match in pattern.finditer(block):
    raw_patterns = match.group(1)
    response = match.group(3)
    action_str = match.group(4)

    # Parse patterns list
    patterns = [p.strip().strip("'\"") for p in raw_patterns.split(',')]
    patterns = [p for p in patterns if p]

    # Unescape JS string escapes
    response = response.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n')

    # Parse action if present
    action = None
    if action_str:
        nav_m = re.search(r"nav:\s*'([^']+)'", action_str)
        label_m = re.search(r"label:\s*'([^']+)'", action_str)
        if nav_m and label_m:
            action = {"nav": nav_m.group(1), "label": label_m.group(1)}

    entry = {"patterns": patterns, "response": response}
    if action:
        entry["action"] = action
    else:
        entry["action"] = None
    entries.append(entry)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(entries, f, indent=2, ensure_ascii=False)

print(f"Extracted {len(entries)} entries to {OUT}")
