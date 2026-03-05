import fitz  # PyMuPDF
import os
import cv2
import numpy as np
import glob

def find_redaction_boxes_in_image(image_bytes):
    """
    Decodes PNG bytes and finds pure black rectangular boxes (>= 17x10).
    Uses a row-by-row scan algorithm handles crosses and ladders by tracking contained runs.
    """
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    if img is None:
        return []
        
    if len(img.shape) == 2:
        gray = img
    elif img.shape[2] == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif img.shape[2] == 4:
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    else:
        gray = img
        
    # threshold for pure black
    mask = gray < 10
    
    boxes = []
    active_runs = {} # (sx, ex) -> {'start_y': y, 'history': []}
    
    height = mask.shape[0]
    
    for y in range(height):
        row_mask = mask[y]
        
        # pad with False to easily find runs using np.diff
        padded = np.concatenate(([False], row_mask, [False]))
        diff = np.diff(padded.astype(np.int8))
        
        run_starts = np.where(diff == 1)[0]
        run_ends = np.where(diff == -1)[0]
        
        current_segments = []
        for sx, ex in zip(run_starts, run_ends):
            if ex - sx >= 17:
                current_segments.append((sx, ex))
                
        next_active_runs = {}
        claimed_current = set()
        
        for run, run_data in active_runs.items():
            sx, ex = run
            survives = False
            survived_csx, survived_cex = None, None
            for (csx, cex) in current_segments:
                # The active run survives if it is mostly contained within a current segment
                if csx <= sx + 2 and cex >= ex - 2:
                    survives = True
                    survived_csx = csx
                    survived_cex = cex
                    break
            
            if survives:
                last_hx, last_hex = run_data['history'][-1]
                if abs((survived_cex - survived_csx) - (last_hex - last_hx)) <= 6:
                    claimed_current.add((survived_csx, survived_cex))
                new_history = run_data['history'] + [(survived_csx, survived_cex)]
                next_active_runs[run] = {'start_y': run_data['start_y'], 'history': new_history}
            else:
                start_y = run_data['start_y']
                h = y - start_y
                if h >= 10:
                    # Filter out circular hole-punches by checking if the top and bottom edges are tapered.
                    core_x = max(hx for hx, _ in run_data['history'])
                    core_ex = min(hex for _, hex in run_data['history'])
                    
                    if core_ex - core_x >= 17:
                        width = int(core_ex - core_x)
                        missing_top = width - int(np.sum(mask[start_y - 1, core_x:core_ex])) if start_y > 0 else width
                        missing_bottom = width - int(np.sum(mask[y, core_x:core_ex])) if y < height else width
                        
                        # If BOTH ends are tapered (small missing pixels, but not 0 since otherwise it would have continued) 
                        if missing_top <= width * 0.3 and missing_bottom <= width * 0.3:
                            pass # Reject tapered shape (circle)
                        else:
                            boxes.append((int(core_x), start_y, width, h))
                    
        for c_run in current_segments:
            if c_run not in claimed_current and c_run not in next_active_runs:
                next_active_runs[c_run] = {'start_y': y, 'history': [(c_run[0], c_run[1])]}
                
        active_runs = next_active_runs
        
    for run, run_data in active_runs.items():
        sx, ex = run
        start_y = run_data['start_y']
        h = height - start_y
        if h >= 10:
            core_x = max(hx for hx, _ in run_data['history'])
            core_ex = min(hex for _, hex in run_data['history'])
            
            if core_ex - core_x >= 17:
                width = int(core_ex - core_x)
                missing_top = width - int(np.sum(mask[start_y - 1, core_x:core_ex])) if start_y > 0 else width
                missing_bottom = width
                if missing_top <= width * 0.3 and missing_bottom <= width * 0.3:
                    pass
                else:
                    boxes.append((int(core_x), start_y, width, h))
            
    def clean_overlapping_boxes(raw_boxes):
        cleaned = []
        for i, (ax, ay, aw, ah) in enumerate(raw_boxes):
            new_ah = ah
            for j, (bx, by, bw, bh) in enumerate(raw_boxes):
                if i == j: continue
                # If B starts during A
                if ay < by < ay + ah:
                    # If B horizontally mostly contains A 
                    if bx <= ax + 2 and bx + bw >= ax + aw - 2:
                        # If B is significantly wider (it's the 'base' of the intersecting T)
                        if bw >= aw + 10:
                            # If they end at roughly the same Y (upward T)
                            if abs((ay + ah) - (by + bh)) <= 5:
                                potential_h = by - ay
                                if potential_h < new_ah:
                                    new_ah = potential_h
            if new_ah >= 10:
                cleaned.append((ax, ay, aw, new_ah))
        return cleaned

    boxes = clean_overlapping_boxes(boxes)
    # Deduplicate and sort
    return sorted(list(set(boxes)), key=lambda b: (b[1], b[0]))

def process_pdfs_in_directory(directory):
    pdf_files = glob.glob(os.path.join(directory, "**", "*.pdf"), recursive=True)
    
    total_total_boxes = 0
    total_pngs_processed = 0
    
    for pdf_path in pdf_files:
        try:
            pdf_document = fitz.open(pdf_path)
        except Exception as e:
            print(f"Error opening PDF: {e}")
            continue
            
        pdf_boxes_count = 0
        
        for page_index in range(len(pdf_document)):
            page = pdf_document.load_page(page_index)
            image_list = page.get_images(full=True)
            
            if image_list:
                for image_index, img in enumerate(image_list):
                    xref = img[0]
                    try:
                        base_image = pdf_document.extract_image(xref)
                        if base_image:
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            
                            if image_ext.lower() == 'png':
                                boxes = find_redaction_boxes_in_image(image_bytes)
                                
                                for bx, by, bw, bh in boxes:
                                    print(f"PDF: {os.path.basename(pdf_path)} | Page {page_index+1} | "
                                          f"Found box | X: {bx}, Y: {by}, Width: {bw} px, Height: {bh} px")
                                    
                                pdf_boxes_count += len(boxes)
                                total_pngs_processed += 1
                                
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        print(f"Error extracting image {image_index+1} on page {page_index+1}: {e}")
                        
        pdf_document.close()
        
        if pdf_boxes_count > 0:
            print(f"Detected {pdf_boxes_count} boxes in {os.path.basename(pdf_path)}")
        total_total_boxes += pdf_boxes_count
        
    print(f"\nSuccessfully processed {total_pngs_processed} PNGs across {len(pdf_files)} PDFs.")
    print(f"Total pure black redaction boxes detected overall: {total_total_boxes}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Searching for PDFs in {script_dir}...")
    process_pdfs_in_directory(script_dir)
