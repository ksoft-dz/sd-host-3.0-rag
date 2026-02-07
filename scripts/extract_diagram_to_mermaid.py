#!/usr/bin/env python3
"""
Simple diagram extractor: detect rectangular nodes and connecting lines/arrows,
apply OCR (pytesseract) when available, and output a Mermaid flowchart.

Usage:
  python scripts/extract_diagram_to_mermaid.py figures/images/FIG_1_1.jpg

Output:
  diagrams/FIG_1_1.mmd
"""
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image
    has_cv = True
except Exception:
    has_cv = False

try:
    import pytesseract
    has_tesseract = True
except Exception:
    has_tesseract = False


def ocr_image(img):
    if not has_tesseract:
        return None
    try:
        # img may be a numpy array (BGR) or PIL.Image
        if isinstance(img, np.ndarray):
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(img_rgb)
        else:
            pil = img
        txt = pytesseract.image_to_string(pil, config='--psm 6')
        txt = txt.strip().replace('\n', ' ').strip()
        return txt if txt else None
    except Exception:
        return None


def detect_boxes_and_lines(image_path: Path):
    if not has_cv:
        raise RuntimeError('OpenCV (cv2) not installed. Install with: pip install opencv-python')

    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f'Failed to read image: {image_path}')

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Find contours (potential boxes)
    contours, _ = cv2.findContours(255 - th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 1000:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        x, y, bw, bh = cv2.boundingRect(approx)
        # Heuristic: rectangles (4 vertices) or reasonably rectangular
        rect_like = len(approx) == 4 or (bw * bh * 0.6 < area < bw * bh * 1.1)
        if rect_like:
            crop = img[y:y+bh, x:x+bw]
            text = ocr_image(crop)
            boxes.append({'bbox': (x, y, bw, bh), 'text': text})

    # Detect lines using probabilistic Hough transform
    edges = cv2.Canny(th, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=30, maxLineGap=15)
    line_list = []
    if lines is not None:
        for l in lines.reshape(-1, 4):
            x1, y1, x2, y2 = l.tolist()
            line_list.append(((x1, y1), (x2, y2)))

    return img, boxes, line_list


def point_in_bbox(pt, bbox):
    x, y = pt
    bx, by, bw, bh = bbox
    return (bx <= x <= bx + bw) and (by <= y <= by + bh)


def build_mermaid(boxes, lines):
    # Assign node ids
    nodes = []
    for i, b in enumerate(sorted(boxes, key=lambda v: (v['bbox'][1], v['bbox'][0]))):
        label = b.get('text') or f'node_{i+1}'
        nid = f'N{i+1}'
        nodes.append({'id': nid, 'label': label, 'bbox': b['bbox']})

    edges = []
    for (p1, p2) in lines:
        src = None
        dst = None
        for n in nodes:
            if point_in_bbox(p1, n['bbox']):
                src = n['id']
            if point_in_bbox(p2, n['bbox']):
                dst = n['id']
        if src and dst and src != dst:
            edges.append((src, dst))

    # Build mermaid text
    lines_out = ['flowchart LR']
    for n in nodes:
        safe_label = n['label'].replace('"', "'")
        lines_out.append(f"    {n['id']}[\"{safe_label}\"]")
    for a, b in edges:
        lines_out.append(f"    {a} --> {b}")

    return '\n'.join(lines_out)


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/extract_diagram_to_mermaid.py <image-path>')
        sys.exit(1)

    img_path = Path(sys.argv[1])
    if not img_path.exists():
        print('Image not found:', img_path)
        sys.exit(1)

    out_dir = Path('diagrams')
    out_dir.mkdir(exist_ok=True)

    try:
        img, boxes, lines = detect_boxes_and_lines(img_path)
    except RuntimeError as e:
        print('Error:', e)
        sys.exit(2)

    if not boxes:
        print('No boxes detected; result may be poor. You can try different image or manually create mermaid.')

    mermaid = build_mermaid(boxes, lines)
    out_path = out_dir / (img_path.stem + '.mmd')
    out_path.write_text(mermaid, encoding='utf-8')

    print('Mermaid diagram written to', out_path)
    print('\n--- Mermaid preview ---\n')
    print(mermaid)

    if not has_tesseract:
        print('\nNote: Tesseract OCR not available; node labels may be generic. Install with:\n')
        print('  pip install pytesseract')
        print('And make sure the Tesseract binary is installed on your system: https://github.com/tesseract-ocr/tesseract')


if __name__ == '__main__':
    main()
