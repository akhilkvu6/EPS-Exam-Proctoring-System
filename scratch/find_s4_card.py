with open('templates/design.html', encoding='utf-8') as f:
    text = f.read()

s4 = text.find('id="buttons"')
print(text[s4:s4+600])
