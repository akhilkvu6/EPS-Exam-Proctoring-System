with open('templates/base.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('Public Guest Header')
print(repr(text[idx-50:idx+350]))
