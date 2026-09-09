import math
import random
import numpy as np
import cv2
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
import opensimplex
import subprocess
import os
import tempfile
from PIL import Image

# Initialize simplex noise
opensimplex.seed(1337)

def extract_logo_points(svg_path, target_width, target_height, num_points):
    """
    Renders SVG to memory using resvg-js (node), applies distance-transform, 
    and samples exactly num_points to preserve pristine shapes.
    """
    temp_png = tempfile.mktemp(suffix=".png")
    
    # We must suppress errors or handle blank SVGs
    try:
        # Call node script
        script_path = os.path.join(os.path.dirname(__file__), "svg2png.js")
        subprocess.run(["node", script_path, str(svg_path), temp_png], check=True, capture_output=True)
        pil_img = Image.open(temp_png).convert("RGBA")
        img_array = np.array(pil_img)
    except Exception as e:
        print(f"Error rendering SVG {svg_path} to PNG via Node: {e}")
        if os.path.exists(temp_png): os.remove(temp_png)
        return np.zeros((num_points, 2), dtype=np.float32)
    finally:
        if os.path.exists(temp_png):
            try: os.remove(temp_png)
            except: pass
    
    # Extract alpha or threshold grayscale
    if img_array.shape[2] == 4:
        mask = img_array[:, :, 3]
    else:
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        mask = cv2.bitwise_not(gray)
        
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    
    y_coords, x_coords = np.nonzero(mask)
    if len(x_coords) == 0:
        return np.zeros((num_points, 2), dtype=np.float32)
        
    min_x, max_x = np.min(x_coords), np.max(x_coords)
    min_y, max_y = np.min(y_coords), np.max(y_coords)
    
    # Distance transform for high-quality sampling
    dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    
    # Grid sampling via binary search to find exact density
    low, high = 1.0, 100.0
    best_pts = []
    
    for _ in range(30):
        mid = (low + high) / 2
        
        xs = np.arange(min_x, max_x + 1, mid)
        ys = np.arange(min_y, max_y + 1, mid)
        
        if len(xs) == 0 or len(ys) == 0:
            continue
            
        xs_int = xs.astype(int)
        ys_int = ys.astype(int)
        
        # clamp
        xs_int = xs_int[xs_int < mask.shape[1]]
        ys_int = ys_int[ys_int < mask.shape[0]]
        
        grid_x, grid_y = np.meshgrid(xs_int, ys_int)
        flat_x, flat_y = grid_x.flatten(), grid_y.flatten()
        
        valid = mask[flat_y, flat_x] > 127
        valid_pts = np.column_stack((flat_x[valid], flat_y[valid]))
        
        if len(valid_pts) >= num_points:
            best_pts = valid_pts
            low = mid
        else:
            high = mid
            
    if len(best_pts) == 0:
        return np.zeros((num_points, 2), dtype=np.float32)
        
    if len(best_pts) > num_points:
        # Sort by distance transform to keep points deepest inside the logo
        dists = dist_transform[best_pts[:, 1], best_pts[:, 0]]
        # Add slight noise to avoid rigid grid borders
        dists = dists + np.random.normal(0, 0.5, len(dists))
        indices = np.argsort(dists)[-num_points:]
        best_pts = best_pts[indices]
    elif len(best_pts) < num_points:
        indices = np.random.choice(len(best_pts), num_points, replace=True)
        best_pts = best_pts[indices]
        
    sampled = best_pts.astype(np.float32)
    
    orig_w = max_x - min_x
    orig_h = max_y - min_y
    # Use 90% of target box to ensure padding
    scale = min(target_width * 0.9 / max(orig_w, 1), target_height * 0.9 / max(orig_h, 1))
    
    # Center the logo in the target box
    sampled[:, 0] = (sampled[:, 0] - (min_x + max_x)/2) * scale + target_width/2
    sampled[:, 1] = (sampled[:, 1] - (min_y + max_y)/2) * scale + target_height/2
    
    return sampled

def coherent_transport(src_pts, dst_pts):
    """
    Spatially coherent optimal transport to prevent particles from crossing entire screen.
    We divide the space into horizontal bands and sort points within.
    """
    def sort_key(pts):
        y_quant = np.round(pts[:, 1] / 8.0)
        keys = y_quant * 10000 + pts[:, 0]
        return np.argsort(keys)
        
    src_idx = sort_key(src_pts)
    dst_idx = sort_key(dst_pts)
    
    mapped_dst = np.zeros_like(dst_pts)
    for i in range(len(src_pts)):
        mapped_dst[src_idx[i]] = dst_pts[dst_idx[i]]
        
    # Apply a quick Hungarian smoothing on small chunks to remove micro-crossings
    chunk_size = 50
    final_dst = np.zeros_like(dst_pts)
    for i in range(0, len(src_pts), chunk_size):
        end = min(i + chunk_size, len(src_pts))
        src_chunk = src_pts[src_idx[i:end]]
        dst_chunk = mapped_dst[src_idx[i:end]]
        
        cost_matrix = cdist(src_chunk, dst_chunk, metric='sqeuclidean')
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        for r, c in zip(row_ind, col_ind):
            final_dst[src_idx[i + r]] = dst_chunk[c]
            
    return final_dst

def compute_traveller_routes(portrait_pts, logo_paths, target_w, target_h, num_points):
    """
    Computes the optimal transport cycle for the travellers.
    Routes are [P0, L1, L2, L3...]
    """
    print(f"Extracting logos...")
    logos = []
    for path in logo_paths:
        pts = extract_logo_points(path, target_w, target_h, num_points)
        logos.append(pts)
        
    if not logos:
        return None
        
    print(f"Computing transport cycle...")
    
    # We want a cycle: P0 -> L1 -> L2 -> ... -> Ln -> P0
    routes = []
    
    # Start with portrait
    if len(portrait_pts) >= num_points:
        idx = np.random.choice(len(portrait_pts), num_points, replace=False)
    else:
        idx = np.random.choice(len(portrait_pts), num_points, replace=True)
    P0 = portrait_pts[idx]
    routes.append(P0)
    
    # Map P0 -> L1
    curr = P0
    for L in logos:
        nxt = coherent_transport(curr, L)
        routes.append(nxt)
        curr = nxt
        
    # We want the loop to end exactly where it started
    # So the last logo must map perfectly back to P0
    P0_final = coherent_transport(curr, P0)
    routes.append(P0_final)
    
    # But wait! For a seamless loop, routes[-1] must EXACTLY equal routes[0] structurally.
    # Actually, P0_final is a reordered P0.
    # To make it truly seamless, we can trace BACKWARDS from P0.
    return compute_backward_traced_routes(P0, logos)

def compute_backward_traced_routes(P0, logos):
    """
    Ensures that routes[-1] == routes[0] exactly.
    """
    routes = [P0]
    curr = P0
    for L in logos:
        nxt = coherent_transport(curr, L)
        routes.append(nxt)
        curr = nxt
        
    # To force the last one to be P0, we map L_last to P0.
    # This gives us a mapping from L_last indices -> P0 indices.
    # If we apply that backwards through the whole chain, everything aligns!
    # A simpler way: just let it map to P0_final, and then reorder the entire chain
    # so that P0_final becomes P0.
    
    # Or even simpler: compute routes forward, then sort ALL routes such that
    # the last route is identical to P0.
    
    P0_final = coherent_transport(curr, P0)
    # P0_final[i] is the location of particle i at the end. It is some permutation of P0.
    # We need P0_final[i] to be exactly P0[i] so the loop closes.
    
    # Build a mapping from P0_final coordinates to P0 indices
    mapping = {}
    for i, pt in enumerate(P0):
        # quantize to avoid float issues
        mapping[(int(pt[0]*10), int(pt[1]*10))] = i
        
    reorder_idx = np.zeros(len(P0), dtype=int)
    for i, pt in enumerate(P0_final):
        key = (int(pt[0]*10), int(pt[1]*10))
        reorder_idx[i] = mapping[key]
        
    # reorder_idx[i] tells us which index in P0 corresponds to particle i.
    # So particle i starts at P0[reorder_idx[i]] and ends at P0_final[i].
    
    # We want particle i to start at P0[i] and end at P0[i].
    # So we invert the permutation!
    
    inv_reorder = np.zeros(len(P0), dtype=int)
    inv_reorder[reorder_idx] = np.arange(len(P0))
    
    final_routes = []
    for r in routes:
        final_routes.append(r[inv_reorder])
        
    final_routes.append(P0) # Perfectly closes the loop
    return final_routes


def generate_fluid_keyframes(p_start, p_end, steps=5, noise_scale=0.015, turbulence=15.0):
    """
    Generates intermediate positions between p_start and p_end
    using 2D curl noise to create a fluid, swirling effect.
    Returns a list of arrays: [p_start, m1, m2, ..., p_end]
    """
    frames = [p_start]
    
    z_offset = random.random() * 100
    
    for i in range(1, steps):
        t = i / steps
        # Easing function for the base trajectory (smootherstep)
        ease_t = t * t * t * (t * (t * 6 - 15) + 10)
        
        base_pos = p_start * (1 - ease_t) + p_end * ease_t
        
        displacements = np.zeros_like(base_pos)
        for j, (x, y) in enumerate(base_pos):
            eps = 1e-4
            
            n1 = opensimplex.noise3(x * noise_scale, (y + eps) * noise_scale, z_offset)
            n2 = opensimplex.noise3(x * noise_scale, (y - eps) * noise_scale, z_offset)
            n3 = opensimplex.noise3((x + eps) * noise_scale, y * noise_scale, z_offset)
            n4 = opensimplex.noise3((x - eps) * noise_scale, y * noise_scale, z_offset)
            
            dx = (n1 - n2) / (2 * eps)
            dy = -(n3 - n4) / (2 * eps)
            
            # Intensity peaks in the middle of the transition
            intensity = turbulence * np.sin(t * np.pi) 
            displacements[j] = [dx * intensity, dy * intensity]
            
        frames.append(base_pos + displacements)
        
    frames.append(p_end)
    return frames


