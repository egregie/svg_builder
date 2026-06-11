import os
import sys
import json
import time
import datetime
import subprocess
import xml.etree.ElementTree as ET
import re

# Ensure we can run it from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def load_design_tokens():
    tokens_path = '00_governance/design-tokens.json'
    if not os.path.exists(tokens_path):
        raise FileNotFoundError(f"Design tokens not found at {tokens_path}")
    with open(tokens_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def log_agent_trace(passport_id, status, duration_ms, error=None):
    trace_path = 'ops/logs/agent_trace.jsonl'
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "agent_id": "A05",
        "skill_id": "svg-qa-gate",
        "input_artifact": f"05_output_svg/staging/{passport_id}_compiled.svg",
        "output_artifact": f"05_output_svg/{passport_id}.svg" if status == "Success" else f"05_output_svg/quarantine/{passport_id}.svg",
        "status": status,
        "duration_ms": int(duration_ms),
        "warnings": [],
        "error": error
    }
    with open(trace_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

def log_qa_failure(passport_id, errors):
    failure_path = 'ops/logs/qa_failures.jsonl'
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "passport_id": passport_id,
        "errors": errors
    }
    with open(failure_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

def run_layer_generation(passport_id, layer_index, engine, output_path):
    print(f"Generating layer {layer_index} using engine {engine}...")
    
    if "VTracer" in engine:
        script = "ops/scripts/vtracer_bridge.py"
    else:
        script = "ops/scripts/starvector_inference.py"
        
    cmd = [sys.executable, script, passport_id, str(layer_index), output_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode != 0:
        print(f"[FAIL] Layer generation failed. stdout: {res.stdout}, stderr: {res.stderr}")
        return False, res.stderr
    print(f"[OK] Layer generated: {output_path}")
    return True, None

def clean_element(elem):
    # Remove namespaces and style/fill attributes to prevent leaks
    tag = elem.tag.split('}')[-1]
    attrib = {}
    
    # Keep only geometrical and structural attributes
    allowed_attribs = ['d', 'x', 'y', 'width', 'height', 'points', 'cx', 'cy', 'r', 'transform']
    for k, v in elem.attrib.items():
        k_clean = k.split('}')[-1]
        if k_clean in allowed_attribs:
            attrib[k_clean] = v
            
    cleaned = ET.Element(tag, **attrib)
    for child in elem:
        cleaned.append(clean_element(child))
    return cleaned

def extract_layer_shapes(layer_svg_path):
    try:
        tree = ET.parse(layer_svg_path)
        root = tree.getroot()
        
        shapes = []
        for child in root:
            tag = child.tag.split('}')[-1]
            if tag in ['path', 'rect', 'polygon', 'circle', 'g']:
                shapes.append(clean_element(child))
        return shapes
    except Exception as e:
        print(f"[ERROR] Failed to parse layer shapes from {layer_svg_path}: {e}")
        return []

def qa_audit_svg(svg_content, design_tokens):
    errors = []
    
    # 1. XML Validity check
    try:
        ET.fromstring(svg_content)
    except Exception as e:
        errors.append(f"Invalid XML syntax: {e}")
        return errors
        
    # Strip the style block for forbidden color audits, as design tokens themselves
    # contain valid token definitions (e.g. --white: #FFFFFF) which should not trigger QA blocks.
    svg_content_audit = re.sub(r'<style>.*?</style>', '', svg_content, flags=re.DOTALL)
    
    # 2. Forbidden colors check (Zero Black Policy)
    # Match any hex colors or color names in the audited SVG text (outside style block)
    hex_colors_audit = re.findall(r'#[0-9a-fA-F]{3,6}', svg_content_audit)
    color_names_audit = re.findall(r'\b(?:black|white|red|green|blue)\b', svg_content_audit.lower())
    
    forbidden = design_tokens.get('forbidden', [])
    for hc in hex_colors_audit:
        if hc.lower() in forbidden:
            errors.append(f"Forbidden color code found: {hc}")
            
    for cn in color_names_audit:
        if cn in forbidden:
            errors.append(f"Forbidden color name found: {cn}")
            
    # Also verify that no raw hex color codes are used outside the <style> block
    if hex_colors_audit:
        errors.append(f"Raw hex color codes found outside the <style> block: {', '.join(hex_colors_audit)}")
                
    return errors

def compile_object_svg(passport_id, design_tokens):
    start_time = time.time()
    
    index_path = f"03_knowledge_graph/{passport_id}.json"
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"Passport index not found: {index_path}")
        
    with open(index_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    resolution = data['resolution']
    width = resolution['width_px']
    height = resolution['height_px']
    
    # 1. Generate layers in staging
    layer_files = []
    for layer in data['layers']:
        layer_idx = layer['layer_index']
        engine = layer['engine']
        layer_svg = f"05_output_svg/staging/{passport_id}_layer_{layer_idx}.svg"
        
        ok, err = run_layer_generation(passport_id, layer_idx, engine, layer_svg)
        if not ok:
            log_agent_trace(passport_id, "Failed", 0, f"Layer {layer_idx} generation failed: {err}")
            return False
        layer_files.append((layer, layer_svg))
        
    # 2. Compile into single composite SVG
    root = ET.Element("svg", 
                      xmlns="http://www.w3.org/2000/svg", 
                      viewBox=f"0 0 {width} {height}", 
                      width=str(width), 
                      height=str(height))
                      
    # Inject design tokens style block
    style = ET.SubElement(root, "style")
    style_content = "\n  :root {\n"
    # Inject colors
    for k, v in design_tokens.get('colors', {}).items():
        style_content += f"    {k}: {v};\n"
    # Inject typography
    for k, v in design_tokens.get('typography', {}).items():
        style_content += f"    {k}: {v};\n"
    # Inject strokes
    for k, v in design_tokens.get('strokes', {}).items():
        style_content += f"    {k}: {v};\n"
    style_content += "  }\n"
    style.text = style_content
    
    # Add shapes from layers
    for layer, filepath in layer_files:
        layer_idx = layer['layer_index']
        color_token = layer['color_token']
        geom_type = layer['geometry_type']
        
        if geom_type == "BoundingRect" and layer_idx == 1:
            # Output solid background rect directly
            ET.SubElement(root, "rect", width=str(width), height=str(height), fill=f"var({color_token})")
        else:
            # Parse layer shapes, clean them, and wrap in a group
            shapes = extract_layer_shapes(filepath)
            if shapes:
                group = ET.SubElement(root, "g", fill=f"var({color_token})")
                for s in shapes:
                    group.append(s)
                    
    # Serialize to string
    # We want to format the XML nicely
    ET.indent(root, space="  ", level=0)
    svg_content = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    # Write to temp staging first
    staging_output = f"05_output_svg/staging/{passport_id}_compiled.svg"
    with open(staging_output, 'w', encoding='utf-8') as f:
        f.write(svg_content)
        
    # 3. QA Audit
    errors = qa_audit_svg(svg_content, design_tokens)
    duration_ms = (time.time() - start_time) * 1000
    
    if errors:
        log_qa_failure(passport_id, errors)
        log_agent_trace(passport_id, "Failed", duration_ms, "; ".join(errors))
        
        # Move to quarantine
        quarantine_path = f"05_output_svg/quarantine/{passport_id}.svg"
        os.makedirs(os.path.dirname(quarantine_path), exist_ok=True)
        with open(quarantine_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
            
        print(f"[FAIL] QA Audit failed for {passport_id}. Moved to quarantine. Errors: {errors}")
        return False
    else:
        # Move to final output
        final_path = f"05_output_svg/{passport_id}.svg"
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
            
        log_agent_trace(passport_id, "Success", duration_ms)
        print(f"[OK] QA Audit passed for {passport_id}. Composite SVG saved to {final_path} ({duration_ms:.1f}ms)")
        return True

def main():
    print("Starting A05: SVG Compiler & QA Auditor script...")
    design_tokens = load_design_tokens()
    
    kg_dir = "03_knowledge_graph"
    if not os.path.exists(kg_dir):
        print(f"Directory {kg_dir} does not exist.")
        return
        
    success_count = 0
    total_count = 0
    
    for file in os.listdir(kg_dir):
        if file.startswith("COMP-") and file.endswith(".json"):
            passport_id = os.path.splitext(file)[0]
            print(f"\n--- Compiling {passport_id} ---")
            total_count += 1
            if compile_object_svg(passport_id, design_tokens):
                success_count += 1
                
    print(f"\n--- Compilation Summary ---")
    print(f"Total compiled: {total_count}")
    print(f"Success (QA Passed): {success_count}")
    print(f"Failed (QA Failed): {total_count - success_count}")

if __name__ == "__main__":
    main()
