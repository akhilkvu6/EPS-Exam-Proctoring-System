import re

css_files = [
    'static/css/design-tokens.css',
    'static/css/bento.css',
    'static/css/styles.css',
    'static/css/design.css',
]

for filepath in css_files:
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    print('==============================', filepath)
    matches = re.findall(r'([^{}]+)\{([^}]+)\}', content)
    for sel, body in matches:
        sel_clean = ' '.join(sel.split())
        if any(k in sel_clean for k in ['btn-danger', 'btn-warning', 'btn-success', 'btn-primary', 'btn-secondary', 'button', '.btn']):
            props = [p.strip() for p in body.split(';') if any(k in p for k in ['background', 'color', 'border'])]
            if props:
                print(f'{sel_clean}  ==>  {"; ".join(props)}')
