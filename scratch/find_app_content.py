with open('templates/base.html', encoding='utf-8') as f:
    text = f.read()

for i, line in enumerate(text.splitlines()):
    if 'app-content' in line:
        print(f'{i+1}: {line}')
