from PIL import Image

for name in ['dark_sec2_matrix.png', 'light_sec2_matrix.png']:
    img = Image.open(f'scratch/{name}')
    print(f'{name}: size={img.size}')
    # Let's sample colors in the action button column (right side of table)
    # The image is the table. The right ~20% contains the action buttons.
    w, h = img.size
    # Sample 4 vertical points for the 4 rows
    # Red row (~20% from top), Orange row (~40%), Green row (~60%), Blue row (~80%)
    for row_pct, expected in [(0.22, 'Red'), (0.42, 'Orange'), (0.62, 'Green'), (0.82, 'Blue')]:
        y = int(h * row_pct)
        # Scan along x from w*0.8 to w*0.95 to find the button color
        found_colors = []
        for x in range(int(w * 0.82), int(w * 0.98), 5):
            pixel = img.getpixel((x, y))
            r, g, b = pixel[:3]
            # Check if saturated color (not grey/black/white)
            if max(r, g, b) - min(r, g, b) > 40:
                found_colors.append((r, g, b))
        if found_colors:
            # take most frequent or median
            sample = found_colors[len(found_colors)//2]
            print(f'  {expected} row button pixel: RGB{sample}')
        else:
            print(f'  {expected} row: NO SATURATED COLOR FOUND!')
