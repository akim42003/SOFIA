from typing import List, Dict

import torch
from PIL import Image
from util.utils import (
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
    """
    Parameters:
    elems : list of raw OmniParser element dicts
    w, h  : int  screenshot width & height

    Returns
    -------
    list[dict]  each element =>
        {
            "id"        : int,                 # 0-based order
            "type"      : "icon" | "text" | …,
            "label"     : str,                 # from `content` if present
            "bbox_px"   : [x1,y1,x2,y2],       # ints in virtual-desk pixels
            "center_px" : (cx,cy)              # ints, ready for pyautogui
        }
    """
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

    return str(elements_pp)
