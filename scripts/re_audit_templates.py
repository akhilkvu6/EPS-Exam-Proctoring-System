import os
import sys
import re
import json
import django

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam.settings')
django.setup()

from django.conf import settings
from django.urls import get_resolver
from accounts import views as acc_views
from exams import views as ex_views
from results import views as res_views
import inspect

templates_dir = os.path.join(settings.BASE_DIR, 'templates')

# 1. Map views to templates
view_to_templates = {}
for mod in [acc_views, ex_views, res_views]:
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        try:
            src = inspect.getsource(obj)
            renders = re.findall(r"render\s*\(\s*request\s*,\s*['\"](.*?)['\"]", src)
            if renders:
                view_to_templates[f"{mod.__name__}.{name}"] = renders
        except Exception:
            pass

# 2. Get all URL patterns
resolver = get_resolver()
def get_routes(urlpatterns, prefix=''):
    r = []
    for p in urlpatterns:
        if hasattr(p, 'url_patterns'):
            r.extend(get_routes(p.url_patterns, prefix + str(p.pattern)))
        else:
            cb = p.callback
            fn = f"{getattr(cb, '__module__', '')}.{getattr(cb, '__name__', str(cb))}"
            r.append({
                'url': '/' + (prefix + str(p.pattern)).lstrip('^'),
                'name': p.name or '',
                'view': fn
            })
    return r

all_routes = get_routes(resolver.url_patterns)

# 3. Discover all templates on disk
all_templates = []
for root, dirs, files in os.walk(templates_dir):
    for f in files:
        if f.endswith('.html'):
            rel = os.path.relpath(os.path.join(root, f), templates_dir).replace('\\', '/')
            all_templates.append(rel)

all_templates.sort()

# 4. In-depth analysis of each template
audit_data = []
categories = {
    'inherits_base': [],
    'standalone_specialized': [],
    'base_shell': [],
    'unresolved_inconsistencies': [],
    'investigation_needed': []
}

for t in all_templates:
    path = os.path.join(templates_dir, t)
    with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
        raw = fp.read()

    lines = raw.splitlines()
    line_count = len(lines)

    extends_match = re.search(r'{%\s*extends\s*[\'"](.*?)[\'"]\s*%}', raw)
    extends = extends_match.group(1) if extends_match else None

    # Check csrf_token in POST forms
    post_forms = re.findall(r'<form[^>]*method=[\'"]?POST[\'"]?[^>]*>', raw, re.IGNORECASE)
    has_post_form = len(post_forms) > 0
    has_csrf = '{% csrf_token %}' in raw or 'csrf_token' in raw

    csrf_missing = has_post_form and not has_csrf

    # CDN / Tailwind
    has_tailwind = 'cdn.tailwindcss.com' in raw
    has_external_fonts = 'fonts.googleapis.com' in raw

    # Blue hex colors
    hex_colors = set(re.findall(r'#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})\b', raw))
    conflict_blues = [c for c in hex_colors if c.lower() in [
        '154ceb', '0036bb', 'edf1fe', '2563eb', '1d4ed8', '3b82f6', '1e40af', '4f46e5', '6366f1', '0d6efd', '0042df', '315efb'
    ]]

    # Duplicate sidebars
    has_aside = bool(re.search(r'<aside\b', raw, re.IGNORECASE))

    # Classes
    uses_bento = any(cls in raw for cls in ['bento-card', 'bento-grid', 'bento-btn', 'bento-table', 'bento-badge'])

    # Find routes rendering this template
    rendered_by_views = [v for v, tmpls in view_to_templates.items() if t in tmpls]
    matched_routes = [r for r in all_routes if r['view'] in rendered_by_views]

    # Classification
    status = 'COMPLIANT'
    notes = []

    if t == 'base.html':
        status = 'BASE_SHELL'
        categories['base_shell'].append(t)
        notes.append('Central application shell layout')
    elif t == 'exams/exam_room.html':
        status = 'STANDALONE_SPECIALIZED'
        categories['standalone_specialized'].append(t)
        notes.append('Intentional fullscreen distraction-free candidate proctoring workspace (uses Sage tokens)')
    elif extends == 'base.html':
        categories['inherits_base'].append(t)
        if conflict_blues:
            status = 'INCONSISTENCY'
            categories['unresolved_inconsistencies'].append(t)
            notes.append(f'Conflicting blue hex colors detected: {conflict_blues}')
        if has_tailwind:
            status = 'INCONSISTENCY'
            categories['unresolved_inconsistencies'].append(t)
            notes.append('Imports external Tailwind CDN')
        if has_aside:
            status = 'INCONSISTENCY'
            categories['unresolved_inconsistencies'].append(t)
            notes.append('Duplicate hardcoded aside navigation')
        if csrf_missing:
            status = 'INVESTIGATION_NEEDED'
            categories['investigation_needed'].append(t)
            notes.append('POST form detected without explicit csrf_token')
    else:
        status = 'INVESTIGATION_NEEDED'
        categories['investigation_needed'].append(t)
        notes.append(f'Does not extend base.html (extends={extends})')

    audit_data.append({
        'template': t,
        'line_count': line_count,
        'extends': extends,
        'status': status,
        'has_post_form': has_post_form,
        'has_csrf': has_csrf,
        'csrf_missing': csrf_missing,
        'has_tailwind': has_tailwind,
        'conflict_blues': conflict_blues,
        'has_aside': has_aside,
        'uses_bento': uses_bento,
        'views': rendered_by_views,
        'routes': [r['url'] for r in matched_routes],
        'notes': notes
    })

print(f"Total Templates Examined: {len(all_templates)}")
print(f"Inherits base.html: {len(categories['inherits_base'])}")
print(f"Base Shell: {len(categories['base_shell'])}")
print(f"Standalone Specialized: {len(categories['standalone_specialized'])}")
print(f"Unresolved Inconsistencies: {len(categories['unresolved_inconsistencies'])}")
print(f"Needs Further Investigation: {len(categories['investigation_needed'])}")

with open('scripts/deep_audit_results.json', 'w', encoding='utf-8') as f:
    json.dump({
        'summary': {
            'total_templates': len(all_templates),
            'total_routes': len(all_routes),
            'inherits_base_count': len(categories['inherits_base']),
            'base_shell_count': len(categories['base_shell']),
            'standalone_specialized_count': len(categories['standalone_specialized']),
            'unresolved_inconsistencies_count': len(categories['unresolved_inconsistencies']),
            'investigation_needed_count': len(categories['investigation_needed'])
        },
        'categories': categories,
        'templates': audit_data
    }, f, indent=2)

print("Saved scripts/deep_audit_results.json successfully.")
