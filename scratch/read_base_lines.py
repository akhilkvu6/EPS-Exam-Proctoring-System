with open('templates/base.html', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
for i in range(275, 345):
    if i < len(lines):
        print(f'{i+1}: {lines[i]}')
