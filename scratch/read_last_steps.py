import json

log_path = r"C:\Users\techm\.gemini\antigravity\brain\d9492c48-3593-438c-bfea-efd119e14a9d\.system_generated\logs\transcript.jsonl"
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            step_idx = data.get("step_index", 0)
            if 11500 <= step_idx <= 11600:
                print(f"[{data.get('source')}][Step {step_idx}][{data.get('type')}]:")
                content = data.get("content")
                if content:
                    print(content[:600] + ("..." if len(content) > 600 else ""))
                else:
                    print("(no content)")
                print("-" * 50)
        except Exception as e:
            pass
