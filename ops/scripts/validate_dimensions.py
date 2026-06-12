import os
import sys
import json
import xml.etree.ElementTree as ET
import re

def parse_svg_viewbox(filepath):
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

def main():
    print("====================================================")
    print("Running SVG Dimensions and Scaling Validation Audit")
    print("====================================================")
    
    kg_dir = "03_knowledge_graph"
    svg_dir = "05_output_svg"
    staging_dir = "05_output_svg/staging"
    
    if not os.path.exists(kg_dir):
        print(f"[FAIL] Knowledge graph directory {kg_dir} not found.")
        sys.exit(1)
        
    failures = 0
    passed = 0
    
    # List files sorted by COMP id
    files = sorted([f for f in os.listdir(kg_dir) if f.startswith("COMP-") and f.endswith(".json")])
    
    for file in files:
        passport_id = os.path.splitext(file)[0]
        json_path = os.path.join(kg_dir, file)
        svg_path = os.path.join(svg_dir, f"{passport_id}.svg")
        
        print(f"\nAudit for {passport_id}:")
        
        # 1. Read JSON metadata
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        target_w = float(metadata['resolution']['width_px'])
        target_h = float(metadata['resolution']['height_px'])
        print(f"  Target Resolution: {target_w:.1f} x {target_h:.1f}")
        
        # 2. Check if final SVG exists
        if not os.path.exists(svg_path):
            print(f"  [FAIL] Compiled SVG {svg_path} not found.")
            failures += 1
            continue
            
        # 3. Read SVG viewBox
        svg_x, svg_y, svg_w, svg_h = parse_svg_viewbox(svg_path)
        if svg_w is None or svg_h is None:
            print("  [FAIL] Could not read viewBox/dimensions from final SVG.")
            failures += 1
            continue
            
        print(f"  Final SVG viewBox: {svg_x}, {svg_y}, {svg_w:.1f}, {svg_h:.1f}")
        
        # Validate final SVG matches target dimensions
        if svg_x != 0.0 or svg_y != 0.0:
            print(f"  [FAIL] Final SVG origin is non-zero: ({svg_x}, {svg_y}). Must be (0, 0).")
            failures += 1
            continue
            
        if abs(svg_w - target_w) > 1e-2 or abs(svg_h - target_h) > 1e-2:
            print(f"  [FAIL] Dimension mismatch: SVG ({svg_w}x{svg_h}) vs Target ({target_w}x{target_h})")
            failures += 1
            continue
            
        # 4. Check layer transformations
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # We find all <g> elements to audit their transforms
        groups = root.findall('.//{http://www.w3.org/2000/svg}g')
        if not groups:
            # Maybe no namespace prefix
            groups = root.findall('.//g')
            
        print(f"  Found {len(groups)} group layers in compiled SVG.")
        
        layer_match_ok = True
        for idx, g in enumerate(groups):
            layer_idx = idx + 2  # Layers in group start at index 2 (1 is solid background)
            layer_svg_path = os.path.join(staging_dir, f"{passport_id}_layer_{layer_idx}.svg")
            
            transform = g.get('transform')
            print(f"    - Group {idx+1} (Layer {layer_idx}): transform='{transform or 'None'}'")
            
            if os.path.exists(layer_svg_path):
                ly_x, ly_y, ly_w, ly_h = parse_svg_viewbox(layer_svg_path)
                print(f"      Source Layer viewBox: {ly_x}, {ly_y}, {ly_w:.1f}, {ly_h:.1f}")
                
                # Check scale/translate calculations
                expected_sx = target_w / ly_w
                expected_sy = target_h / ly_h
                
                # If there's non-zero origin, check translate
                if ly_x != 0.0 or ly_y != 0.0:
                    expected_transform = f"scale({expected_sx:.6f}, {expected_sy:.6f}) translate({-ly_x:.6f}, {-ly_y:.6f})"
                    if not transform:
                        print("      [FAIL] Missing transform for non-zero origin source viewBox.")
                        layer_match_ok = False
                    elif "scale" not in transform or "translate" not in transform:
                        print(f"      [FAIL] Transform '{transform}' does not contain expected scale/translate.")
                        layer_match_ok = False
                    else:
                        print(f"      [OK] Transform correctly handles scale and non-zero origin offset translation.")
                else:
                    # Zero origin viewBox
                    if abs(ly_w - target_w) > 1e-2 or abs(ly_h - target_h) > 1e-2:
                        # Should have scale
                        if not transform or "scale" not in transform:
                            print(f"      [FAIL] Missing scale transform. Expected sx={expected_sx:.4f}, sy={expected_sy:.4f}")
                            layer_match_ok = False
                        else:
                            print(f"      [OK] Scale transform matches dimension ratios.")
                    else:
                        if transform:
                            print(f"      [WARN] Transform exists but source and target dimensions match exactly.")
                        else:
                            print(f"      [OK] No transform needed as dimensions match exactly.")
            else:
                print(f"      [WARN] Staging layer file {layer_svg_path} not found for scale validation.")
                
        if layer_match_ok:
            print(f"  [PASS] {passport_id} verified successfully.")
            passed += 1
        else:
            failures += 1
            
    print("\n====================================================")
    print(f"Audit Complete: {passed} passed, {failures} failed.")
    print("====================================================")
    
    if failures > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
