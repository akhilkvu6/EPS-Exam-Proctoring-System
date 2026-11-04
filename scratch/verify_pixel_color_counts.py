from PIL import Image

def analyze_image(path):
    img = Image.open(path)
    w, h = img.size
    print('==============================', path)
    red_count = 0
    green_count = 0
    orange_count = 0
    blue_count = 0
    
    for y in range(0, h):
        for x in range(0, w):
            r, g, b = img.getpixel((x, y))[:3]
            # Red: r high, g and b low
            if r > 180 and g < 90 and b < 90:
                red_count += 1
            # Green: g high, r and b low
            elif g > 150 and r < 100 and b < 120:
                green_count += 1
            # Orange: r high, g around 70-140, b low
            elif r > 200 and 70 <= g <= 150 and b < 60:
                orange_count += 1
            # Blue: b high, r low
            elif b > 200 and r < 100:
                blue_count += 1

    print(f"  Red pixels:    {red_count}")
    print(f"  Orange pixels: {orange_count}")
    print(f"  Green pixels:  {green_count}")
    print(f"  Blue pixels:   {blue_count}")

for img_name in ['light_sec2_matrix_view.png', 'dark_sec2_matrix_view.png', 'light_sec4_buttons_view.png', 'dark_sec4_buttons_view.png']:
    analyze_image('scratch/' + img_name)
