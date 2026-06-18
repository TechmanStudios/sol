import os
import re
import json
from pathlib import Path

def parse_yaml_frontmatter(content):
    # Match frontmatter that might be inside a ```chatagent block or just plain ---
    frontmatter_pattern = re.compile(r'(?:```(?:chatagent)?\s*)?---\s*(.*?)\s*---\s*(?:```)?', re.DOTALL)
    match = frontmatter_pattern.search(content)
    if not match:
        return {}, content
    
    yaml_text = match.group(1)
    body_text = content[match.end():].strip()
    
    # Simple manual YAML parser to avoid external dependencies
    metadata = {}
    current_key = None
    list_items = []
    
    for line in yaml_text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        # Check if list item
        if line_stripped.startswith('-') and current_key:
            # Check if it's a simple list or dictionary item
            item_val = line_stripped[1:].strip()
            if ':' in item_val:
                # Part of key-value list (like handoffs)
                if not isinstance(metadata[current_key], list):
                    metadata[current_key] = []
                # Simple parser for list of dicts (label: value, agent: value, etc.)
                # e.g., "- label: Research" or "  agent: soltech-research"
                pass # Will handle below
            else:
                if not isinstance(metadata.get(current_key), list):
                    metadata[current_key] = []
                # Clean up quotes if present
                clean_val = item_val.strip("'\"")
                metadata[current_key].append(clean_val)
            continue
            
        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip()
            val = parts[1].strip()
            
            # Check if it starts a list or dict block or inline list
            if val.startswith('[') and val.endswith(']'):
                # Inline JSON array of strings
                try:
                    # Clean up single quotes to double quotes for JSON parsing
                    json_val = val.replace("'", '"')
                    metadata[key] = json.loads(json_val)
                except Exception:
                    # Fallback basic parsing
                    items = [item.strip(" '\"") for item in val[1:-1].split(',')]
                    metadata[key] = items
                current_key = key
            elif val == '':
                metadata[key] = []
                current_key = key
            else:
                metadata[key] = val.strip("'\"")
                current_key = key
                
    # A second pass specifically for parsing list of dicts (like handoffs)
    # This is more robust for handoffs:
    # handoffs:
    #   - label: Research
    #     agent: soltech-research
    #     prompt: Hand off research and analysis tasks
    if 'handoffs' in metadata:
        handoffs = []
        current_handoff = None
        yaml_lines = yaml_text.splitlines()
        in_handoffs = False
        
        for line in yaml_lines:
            indent = len(line) - len(line.lstrip())
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            if line_stripped.startswith('handoffs:'):
                in_handoffs = True
                continue
            elif in_handoffs and indent == 0:
                in_handoffs = False
                
            if in_handoffs:
                if line_stripped.startswith('-'):
                    if current_handoff:
                        handoffs.append(current_handoff)
                    current_handoff = {}
                    # Parse inline key value if present, e.g. "- label: Research"
                    item_content = line_stripped[1:].strip()
                    if ':' in item_content:
                        k, v = item_content.split(':', 1)
                        current_handoff[k.strip()] = v.strip().strip("'\"")
                elif ':' in line_stripped and current_handoff is not None:
                    k, v = line_stripped.split(':', 1)
                    current_handoff[k.strip()] = v.strip().strip("'\"")
                    
        if current_handoff:
            handoffs.append(current_handoff)
        metadata['handoffs'] = handoffs
        
    return metadata, body_text

def parse_markdown_sections(body):
    sections = {}
    current_section = "General"
    sections[current_section] = []
    
    # Split by headings
    heading_pattern = re.compile(r'^(#{1,6})\s+(.*?)$', re.MULTILINE)
    last_pos = 0
    matches = list(heading_pattern.finditer(body))
    
    if not matches:
        sections["General"] = body
        return sections
        
    # Content before first heading
    first_heading_start = matches[0].start()
    if first_heading_start > 0:
        sections["General"] = body[:first_heading_start].strip()
        
    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        
        start_pos = match.end()
        end_pos = matches[i+1].start() if i < len(matches) - 1 else len(body)
        
        content = body[start_pos:end_pos].strip()
        # Key on clean heading title
        sections[title] = content
        
    return sections

def main():
    agents_dir = Path("g:/docs/TechmanStudios/sol/.github/agents")
    output_path = Path("g:/docs/TechmanStudios/sol/scratch/sol_agents_data.json")
    
    agent_files = list(agents_dir.glob("**/*.agent.md"))
    print(f"Found {len(agent_files)} agent files.")
    
    parsed_agents = []
    
    for agent_file in agent_files:
        print(f"Parsing {agent_file.relative_to(agents_dir)}")
        with open(agent_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        metadata, body = parse_yaml_frontmatter(content)
        sections = parse_markdown_sections(body)
        
        # Determine name from metadata or filename
        name = metadata.get("name") or agent_file.stem.replace(".agent", "")
        description = metadata.get("description") or ""
        tools = metadata.get("tools") or []
        handoffs = metadata.get("handoffs") or []
        
        parsed_agents.append({
            "name": name,
            "filename": agent_file.name,
            "filepath": str(agent_file.as_posix()),
            "description": description,
            "tools": tools,
            "handoffs": handoffs,
            "sections": sections,
            "raw_body": body
        })
        
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed_agents, f, indent=2)
        
    print(f"Successfully wrote parsed agent data to {output_path}")

if __name__ == "__main__":
    main()
