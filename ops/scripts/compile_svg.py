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

def parse_hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join([c*2 for c in hex_str])
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (0, 0, 0)

def get_closest_color_token(hex_color, design_tokens):
    if not hex_color or not hex_color.startswith('#'):
        return None
    rgb = parse_hex_to_rgb(hex_color)
    
    closest_token = None
    min_dist = float('inf')
    for token, hex_val in design_tokens.get('colors', {}).items():
        token_rgb = parse_hex_to_rgb(hex_val)
        dist = sum((a - b)**2 for a, b in zip(rgb, token_rgb))
        if dist < min_dist:
            min_dist = dist
            closest_token = token
    return closest_token

def parse_style_str(style_str):
    props = {}
    if not style_str:
        return props
    for item in style_str.split(';'):
        if ':' in item:
            k, v = item.split(':', 1)
            props[k.strip().lower()] = v.strip()
    return props

def get_inherited_attribute(elem, attr_name, parent_map):
    curr = elem
    while curr is not None:
        val = curr.get(attr_name)
        if val:
            return val
        style = curr.get('style')
        if style:
            props = parse_style_str(style)
            if attr_name in props:
                return props[attr_name]
        curr = parent_map.get(curr)
    return None

def get_element_fill(elem, parent_map):
    val = get_inherited_attribute(elem, 'fill', parent_map)
    if val == 'none':
        return None
    return val

def is_inside_defs(elem, parent_map):
    curr = elem
    while curr in parent_map:
        curr = parent_map[curr]
        tag = curr.tag.split('}')[-1]
        if tag in ['defs', 'clipPath', 'style']:
            return True
    return False

def is_inside_text(elem, parent_map):
    curr = elem
    while curr in parent_map:
        curr = parent_map[curr]
        tag = curr.tag.split('}')[-1]
        if tag == 'text':
            return True
    return False

def clean_element(elem, design_tokens):
    tag = elem.tag.split('}')[-1]
    attrib = {}
    
    style_props = {}
    if 'style' in elem.attrib:
        style_props = parse_style_str(elem.attrib['style'])
        
    combined_attrib = {}
    for k, v in elem.attrib.items():
        k_clean = k.split('}')[-1]
        if k_clean != 'style':
            combined_attrib[k_clean] = v
            
    for k, v in style_props.items():
        combined_attrib[k] = v
        
    allowed_attribs = [
        'd', 'x', 'y', 'width', 'height', 'points', 'cx', 'cy', 'r', 'rx', 'ry', 
        'x1', 'y1', 'x2', 'y2', 'transform', 
        'font-family', 'font-size', 'text-anchor', 'font-weight', 'dx', 'dy', 'rotate',
        'stroke-width', 'stroke-miterlimit', 'letter-spacing'
    ]
    
    for k, v in combined_attrib.items():
        if k in allowed_attribs:
            attrib[k] = v
        elif k == 'fill':
            if v == 'none':
                attrib['fill'] = 'none'
            elif v.startswith('#'):
                token = get_closest_color_token(v, design_tokens)
                if token:
                    attrib['fill'] = f"var({token})"
            else:
                attrib['fill'] = v
        elif k == 'stroke':
            if v == 'none':
                attrib['stroke'] = 'none'
            elif v.startswith('#'):
                token = get_closest_color_token(v, design_tokens)
                if token:
                    attrib['stroke'] = f"var({token})"
            else:
                attrib['stroke'] = v
                
    cleaned = ET.Element(tag, **attrib)
    if elem.text:
        cleaned.text = elem.text
    if elem.tail:
        cleaned.tail = elem.tail
        
    for child in elem:
        cleaned.append(clean_element(child, design_tokens))
    return cleaned

def extract_layer_shapes(layer_svg_path, target_color_token, design_tokens):
    tree = ET.parse(layer_svg_path)
    root = tree.getroot()
    
    parent_map = {c: p for p in root.iter() for c in p}
    shapes = []
    allowed_tags = ['path', 'rect', 'polygon', 'circle', 'ellipse', 'polyline', 'line', 'text', 'tspan']
    
    for elem in root.iter():
        tag = elem.tag.split('}')[-1]
        if tag in allowed_tags:
            if is_inside_defs(elem, parent_map) or is_inside_text(elem, parent_map):
                continue
                
            fill = get_element_fill(elem, parent_map)
            if fill:
                closest_token = get_closest_color_token(fill, design_tokens)
                if closest_token and closest_token != target_color_token:
                    print(f"  [FILTER] Discarding element {tag} with fill {fill} (mapped to {closest_token}, target is {target_color_token})")
                    continue
            shapes.append(clean_element(elem, design_tokens))
    return shapes

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
    
    # Strip any design token references (e.g. var(--white), var(--dark)) to avoid false positives on token names
    svg_content_audit = re.sub(r'var\(--[a-zA-Z0-9-]+\)', '', svg_content_audit)
    
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
                
def get_svg_viewbox(filepath):
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        viewbox = root.get('viewBox')
        if viewbox:
            parts = [float(x) for x in re.split(r'[\s,]+', viewbox.strip()) if x]
            if len(parts) == 4:
                return parts[0], parts[1], parts[2], parts[3]
        width = root.get('width')
        height = root.get('height')
        if width and height:
            w_val = float(re.sub(r'[^\d.]', '', width))
            h_val = float(re.sub(r'[^\d.]', '', height))
            return 0.0, 0.0, w_val, h_val
    except Exception as e:
        print(f"[WARN] Failed to parse SVG viewBox from {filepath}: {e}")
    return 0.0, 0.0, None, None

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
        
        if os.path.exists(layer_svg):
            print(f"Layer {layer_idx} already exists at {layer_svg}. Skipping generation (using cached).")
            ok, err = True, None
        else:
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
            shapes = extract_layer_shapes(filepath, color_token, design_tokens)
            if not shapes:
                raise ValueError(f"Foreground layer {layer_idx} has no shapes extracted (empty layer).")
                
            # Determine scaling and translation offsets
            x_min, y_min, source_w, source_h = get_svg_viewbox(filepath)
            scale_attrib = {}
            if source_w and source_h:
                sx = width / source_w
                sy = height / source_h
                if x_min != 0.0 or y_min != 0.0:
                    scale_attrib["transform"] = f"scale({sx:.6f}, {sy:.6f}) translate({-x_min:.6f}, {-y_min:.6f})"
                elif abs(source_w - width) > 1e-2 or abs(source_h - height) > 1e-2:
                    scale_attrib["transform"] = f"scale({sx:.6f}, {sy:.6f})"
                
            group = ET.SubElement(root, "g", fill=f"var({color_token})", **scale_attrib)
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
            try:
                if compile_object_svg(passport_id, design_tokens):
                    success_count += 1
            except Exception as e:
                import traceback
                err_msg = f"Compilation failed: {e}\n{traceback.format_exc()}"
                print(f"[FAIL] Error compiling {passport_id}: {e}")
                log_qa_failure(passport_id, [f"Compilation error: {e}"])
                log_agent_trace(passport_id, "Failed", 0, err_msg)
                
    print(f"\n--- Compilation Summary ---")
    print(f"Total compiled: {total_count}")
    print(f"Success (QA Passed): {success_count}")
    print(f"Failed (QA Failed): {total_count - success_count}")

if __name__ == "__main__":
    main()
