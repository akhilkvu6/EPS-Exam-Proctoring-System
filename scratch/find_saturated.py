from PIL import Image

img = Image.open('scratch/dark_sec2_matrix.png')
w, h = img.size

# Let's see what saturated colors exist in the entire image!
saturated = []
for y in range(0, h, 2):
    for x in range(0, w, 2):
        p = img.getpixel((x, y))
        r, g, b = p[:3]
        if max(r, g, b) - min(r, g, b) > 50:
            saturated.append((x, y, (r, g, b)))

print('Total saturated pixels in dark_sec2_matrix.png:', len(saturated))
if saturated:
    # Print sample
    print('Sample saturated pixels:', saturated[:10])
    # Check bounding box of saturated pixels
    xs = [pt[0] for pt in saturated]
    ys = [pt[1] for pt in saturated]
    print(f'Saturated X range: {min(xs)} to {max(xs)}, Y range: {min(ys)} to {max(ys)}')
