from typing import List, Dict

import torch
from PIL import Image
from sofia.vision.utils import (
    check_ocr_box,
    get_yolo_model,
    get_caption_model_processor,
    get_som_labeled_img,
)

# ─── weights are loaded once at import ───────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
yolo_model = get_yolo_model(model_path="weights/icon_detect/model.pt")
caption_model_processor = get_caption_model_processor(
    model_name="florence2",
    model_name_or_path="weights/icon_caption_florence"
)
# caption_model_processor = get_caption_model_processor(
#     model_name="blip2", model_name_or_path="weights/icon_caption_blip2"
# )


# ─── helper: ensure bbox is pixels, then add center_px ──────────────
def postprocess_elements(elems: List[Dict], w: int, h: int) -> List[Dict]:

    cleaned = []
    for idx, e in enumerate(elems):
        x1, y1, x2, y2 = e["bbox"]

        # If coords ≤1, treat as ratio and convert to pixels
        if max(x1, x2, y1, y2) <= 1.01:
            x1, x2 = x1 * w, x2 * w
            y1, y2 = y1 * h, y2 * h

        bbox_px   = [int(x1), int(y1), int(x2), int(y2)]
        center_px = ((bbox_px[0] + bbox_px[2]) // 2,
                     (bbox_px[1] + bbox_px[3]) // 2)

        cleaned.append({
            "id"        : idx,
            "type"      : e.get("type", "unknown"),
            "label"     : e.get("content", ""),
            "bbox_px"   : bbox_px,
            "center_px" : center_px,
        })

    return cleaned


# ─── improved LLM-friendly output formatting ────────────────────────
def format_for_llm(elements: List[Dict], screen_width: int, screen_height: int) -> str:
    """
    Convert raw element data into a clean, structured format optimized for computer use.
    Preserves all interactable elements with precise coordinates while filtering only obvious noise.
    """
    if not elements:
        return "No UI elements detected on screen."
    
    # Classify elements - preserve ALL potentially interactable elements
    interactable_elements = []
    text_elements = []
    
    for elem in elements:
        label = elem.get('label', '').strip()
        elem_type = elem.get('type', 'unknown')
        bbox = elem.get('bbox_px', [])
        
        # Skip only truly empty or corrupted elements
        if not label and elem_type == 'unknown':
            continue
            
        # Calculate element size
        width = height = 0
        if len(bbox) == 4:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        
        # Classify as interactable if:
        # 1. Detected as button/icon type
        # 2. Contains UI symbols (even single chars like ×, +, −)
        # 3. Has typical button/UI dimensions
        # 4. Contains action-related keywords
        is_interactable = (
            elem_type in ['button', 'icon', 'link', 'input', 'checkbox', 'dropdown'] or
            label in ['×', '−', '+', '⋮', '📁', '🔍', '⚙️', '▶', '⏸', '⏹', '🔄', '↗', '↖', '↙', '↘'] or
            any(term in label.lower() for term in ['button', 'click', 'menu', 'tab', 'close', 'save', 'edit', 'delete', 'add', 'remove', 'open', 'file', 'folder']) or
            (width >= 15 and height >= 15 and width <= 200 and height <= 80) or  # Typical button dimensions
            (width >= 10 and height >= 10 and len(label) <= 3)  # Small icons/symbols
        )
        
        if is_interactable:
            interactable_elements.append(elem)
        else:
            # Only keep text elements that aren't too small (likely important labels)
            if width >= 10 and height >= 8:
                text_elements.append(elem)
    
    # Combine but prioritize interactable elements
    important_elements = interactable_elements + text_elements
    
    # Group elements by screen regions
    regions = {
        'top': [],      # Top 25% of screen
        'middle': [],   # Middle 50% of screen  
        'bottom': []    # Bottom 25% of screen
    }
    
    top_threshold = screen_height * 0.25
    bottom_threshold = screen_height * 0.75
    
    for elem in important_elements:
        y_center = elem['center_px'][1]
        if y_center < top_threshold:
            regions['top'].append(elem)
        elif y_center > bottom_threshold:
            regions['bottom'].append(elem)
        else:
            regions['middle'].append(elem)
    
    # Build clean output
    output_lines = []
    
    # Screen summary
    total_elements = len(important_elements)
    output_lines.append(f"SCREEN ANALYSIS ({screen_width}x{screen_height} pixels, {total_elements} key elements)")
    
    # Process each region
    for region_name, region_elements in regions.items():
        if not region_elements:
            continue
            
        output_lines.append(f"\n{region_name.upper()} REGION:")
        
        # Sort by importance - longer text often means more important
        sorted_elements = sorted(region_elements, 
                               key=lambda x: len(x.get('label', '')), 
                               reverse=True)
        
        for elem in sorted_elements[:15]:  # Increased limit for more coverage
            label = elem.get('label', 'Unknown')
            elem_type = elem.get('type', 'unknown')
            center_x, center_y = elem['center_px']
            bbox = elem.get('bbox_px', [])
            
            # Check if this is an interactable element
            is_interactable = elem in interactable_elements
            
            # Convert to relative position
            rel_x = "left" if center_x < screen_width * 0.33 else "right" if center_x > screen_width * 0.67 else "center"
            rel_y = "top" if center_y < screen_height * 0.33 else "bottom" if center_y > screen_height * 0.67 else "middle"
            
            # Format clean output
            position_desc = f"{rel_x}-{rel_y}" if rel_x != "center" or rel_y != "middle" else "center"
            
            # Clean up the label
            clean_label = label.replace('\n', ' ').replace('\r', ' ').strip()
            if len(clean_label) > 45:
                clean_label = clean_label[:42] + "..."
            
            # Include pixel coordinates for interactable elements
            if is_interactable:
                output_lines.append(f"  • [{elem_type.upper()}] {clean_label} | CLICK: ({center_x}, {center_y}) | {position_desc}")
            else:
                output_lines.append(f"  • {clean_label} ({position_desc})")
    
    # Add comprehensive interactable elements summary
    if interactable_elements:
        output_lines.append(f"\nINTERACTABLE ELEMENTS ({len(interactable_elements)} found):")
        
        # Group by type for better organization
        by_type = {}
        for elem in interactable_elements:
            elem_type = elem.get('type', 'unknown')
            if elem_type not in by_type:
                by_type[elem_type] = []
            by_type[elem_type].append(elem)
        
        # Display each type
        for elem_type, type_elements in by_type.items():
            output_lines.append(f"  {elem_type.upper()}S ({len(type_elements)}):")
            for elem in type_elements[:8]:  # Limit per type to avoid overwhelming
                label = elem.get('label', 'Unlabeled')
                center_x, center_y = elem['center_px']
                bbox = elem.get('bbox_px', [])
                
                # Clean label
                clean_label = label.replace('\n', ' ').replace('\r', ' ').strip()
                if len(clean_label) > 30:
                    clean_label = clean_label[:27] + "..."
                
                # Add size info for context
                size_info = ""
                if len(bbox) == 4:
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    size_info = f" ({width}x{height})"
                
                output_lines.append(f"    → {clean_label} | CLICK: ({center_x}, {center_y}){size_info}")
    
    # Add screen dimensions reminder for agent
    output_lines.append(f"\nSCREEN INFO: {screen_width}x{screen_height} pixels")
    output_lines.append("NOTE: Use CLICK coordinates (x, y) with click_mouse and move_mouse tools")
    
    return "\n".join(output_lines)


# ─── main entry called by ChatBrain ─────────────────────────────────
def process_image(image_path: str):

    img = Image.open(image_path)
    W, H = img.size

    # OmniParser config
    box_overlay_ratio = W / 3200
    draw_cfg = {
        "text_scale": 0.8 * box_overlay_ratio,
        "text_thickness": max(int(2 * box_overlay_ratio), 1),
        "text_padding": max(int(3 * box_overlay_ratio), 1),
        "thickness": max(int(3 * box_overlay_ratio), 1),
    }

    ocr_bbox_rslt, _ = check_ocr_box(
        img, display_img=False, output_bb_format="xyxy",
        easyocr_args={"paragraph": False, "text_threshold": 0.9},
        use_paddleocr=True
    )
    ocr_text, ocr_bbox = ocr_bbox_rslt

    # NOTE: output_coord_in_ratio=False ⇒ YOLO returns pixel coords already
    overlay_b64, label_coords, elements = get_som_labeled_img(
        img,
        yolo_model,
        BOX_TRESHOLD=0.1,
        output_coord_in_ratio=False,
        ocr_bbox=ocr_bbox,
        draw_bbox_config=draw_cfg,
        caption_model_processor=caption_model_processor,
        ocr_text=ocr_text,
        iou_threshold=0.01,
        imgsz=1920,
    )
    # post-process boxes
    elements_pp = postprocess_elements(elements, W, H)

    # Use improved LLM-friendly output format
    return format_for_llm(elements_pp, W, H)
