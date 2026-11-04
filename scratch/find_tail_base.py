with open('templates/base.html', encoding='utf-8') as f:
    text = f.read()

for i, line in enumerate(text.splitlines()[-40:]):
    print(line)
