with open('templates/base.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('public-footer')
print(text[idx-50:idx+800])
