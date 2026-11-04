from PIL import Image

img = Image.open('scratch/dark_sec2_matrix.png')
colors = img.getcolors(maxcolors=100000)
print('Total unique colors:', len(colors))
# Sort by count
colors.sort(key=lambda x: x[0], reverse=True)
for count, col in colors[:15]:
    print(f'Count {count}: {col}')
