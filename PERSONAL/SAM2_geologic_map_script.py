#%%IMPORT LIBRARIES

import os
# if using Apple MPS, fall back to CPU for unsupported ops
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
import numpy as np
import torch
import matplotlib
matplotlib.use('TkAgg')  # or 'Qt5Agg'
import matplotlib.pyplot as plt
from PIL import Image

#%%SELECT COMPUTATION DEVICE

if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"using device: {device}")

if device.type == "cuda":
    # use bfloat16 for the entire notebook
    torch.autocast("cuda", dtype=torch.bfloat16).__enter__()
    # turn on tfloat32 for Ampere GPUs (https://pytorch.org/docs/stable/notes/cuda.html#tensorfloat-32-tf32-on-ampere-devices)
    if torch.cuda.get_device_properties(0).major >= 8:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
elif device.type == "mps":
    print(
        "\nSupport for MPS devices is preliminary. SAM 2 is trained with CUDA and might "
        "give numerically different outputs and sometimes degraded performance on MPS. "
        "See e.g. https://github.com/pytorch/pytorch/issues/84936 for a discussion."
    )


#%% DEFINE VIS FUNCTIONS

np.random.seed(3)

def show_mask(mask, ax, random_color=False, borders = True):
    if random_color:
        color = np.concatenate([np.random.random(3), np.array([0.6])], axis=0)
    else:
        color = np.array([30/255, 144/255, 255/255, 0.6])
    h, w = mask.shape[-2:]
    mask = mask.astype(np.uint8)
    mask_image =  mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    if borders:
        import cv2
        contours, _ = cv2.findContours(mask,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) 
        # Try to smooth contours
        contours = [cv2.approxPolyDP(contour, epsilon=0.01, closed=True) for contour in contours]
        mask_image = cv2.drawContours(mask_image, contours, -1, (1, 1, 1, 0.5), thickness=2) 
    ax.imshow(mask_image)

def show_points(coords, labels, ax, marker_size=375):
    pos_points = coords[labels==1]
    neg_points = coords[labels==0]
    ax.scatter(pos_points[:, 0], pos_points[:, 1], color='green', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)
    ax.scatter(neg_points[:, 0], neg_points[:, 1], color='red', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)   

def show_box(box, ax):
    x0, y0 = box[0], box[1]
    w, h = box[2] - box[0], box[3] - box[1]
    ax.add_patch(plt.Rectangle((x0, y0), w, h, edgecolor='green', facecolor=(0, 0, 0, 0), lw=2))    

def show_masks(image, masks, scores, point_coords=None, box_coords=None, input_labels=None, borders=True):
    for i, (mask, score) in enumerate(zip(masks, scores)):
        plt.figure(figsize=(10, 10))
        plt.imshow(image)
        show_mask(mask, plt.gca(), borders=borders)
        if point_coords is not None:
            assert input_labels is not None
            show_points(point_coords, input_labels, plt.gca())
        if box_coords is not None:
            # boxes
            show_box(box_coords, plt.gca())
        if len(scores) > 1:
            plt.title(f"Mask {i+1}, Score: {score:.3f}", fontsize=18)
        plt.axis('off')
        plt.show()


#%% LOAD/PREVIEW IMAGE

image = Image.open('images/map.png')
image = np.array(image.convert("RGB"))

plt.figure(figsize=(10, 10))
plt.imshow(image)
plt.axis('on')
plt.show()


#%% LOAD SAM-2

from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

sam2_checkpoint = "../checkpoints/sam2_hiera_large.pt"
model_cfg = "sam2_hiera_l.yaml"

sam2_model = build_sam2(model_cfg, sam2_checkpoint, device=device)

predictor = SAM2ImagePredictor(sam2_model)

predictor.set_image(image)

#%% SELECT POINTS


number_points = 0  # Initialize the number of points

points = []
labels = []

def onclick(event):
    global number_points  # Use global to update the variable
    if event.xdata is None or event.ydata is None:  # Ignore clicks outside the plot
        return
    if event.button == 1:  # Left-click to add a point
        points.append((event.xdata, event.ydata))
        labels.append(1)  # Always use 1 to indicate a new object
        plt.plot(event.xdata, event.ydata, 'go')
        plt.draw()
        number_points += 1  # Increment the point count
    elif event.button == 3 and points:  # Right-click to remove the last point
        points.pop()
        labels.pop()
        plt.clf()
        plt.imshow(image)
        plt.title('Click to select points, right-click to undo. Press Enter to finish.')
        plt.axis('on')
        for p in points:
            plt.plot(p[0], p[1], 'go')
        plt.draw()
        number_points -= 1  # Decrement the point count

def on_key(event):
    if event.key == 'enter':
        plt.close()  # Close the interactive window

# Display the image
fig, ax = plt.subplots()
ax.imshow(image)
plt.title('Click to select points, right-click to undo. Press Enter to finish.')
plt.axis('on')

# Connect the click and key press events
cid_click = fig.canvas.mpl_connect('button_press_event', onclick)
cid_key = fig.canvas.mpl_connect('key_press_event', on_key)

# Wait for the user to finish
plt.show()

# Convert points and labels to NumPy arrays
input_points = np.array(points).reshape(number_points, 1, 2)  # Reshape to Bx1x2 format
input_labels = np.array(labels).reshape(number_points, 1)     # Reshape to Bx1 format

#%% SHOW POINT(S)

plt.figure(figsize=(10, 10))
plt.imshow(image)
show_points(input_points, input_labels, plt.gca())
plt.axis('on')
plt.show()  

print(predictor._features["image_embed"].shape, predictor._features["image_embed"][-1].shape)

#%% PROCESS MULTIPLE SEPARATE POINTS

masks, scores, _ = predictor.predict(
    point_coords=input_points,
    point_labels=input_labels,
    multimask_output=False,
)

image_points = input_points
print(image_points.shape) # Bx1x2 where B corresponds to number of objects 
image_labels = np.ones((number_points, 1), dtype=int)  # Shape (number_points, 1)
print(image_labels.shape) # Bx1 where B corresponds to number of objects 
image_masks = masks
print(image_masks.shape)  # (batch_size) x (num_predicted_masks_per_input) x H x W


#%% DISPLAY MASKS
plt.figure(figsize=(10, 10))
plt.imshow(image)

# Iterate over each set of points, labels, and masks
for points, labels, masks_per_point in zip(image_points, image_labels, image_masks):
    for mask in masks_per_point:  # Loop over masks for the current point
        show_mask(mask, plt.gca(), random_color=True)
    show_points(points, labels, plt.gca())  # Plot points for the current batch

plt.axis('off')
plt.show()  # Display the plot after all masks and points are plotted

