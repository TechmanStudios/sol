import json

log_path = r"C:\Users\techm\.gemini\antigravity\brain\d9492c48-3593-438c-bfea-efd119e14a9d\.system_generated\logs\transcript.jsonl"
with open(log_path, "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("type") == "USER_INPUT":
                print(f"Step {data.get('step_index')}: {data.get('content')}")
        except Exception as e:
            pass
