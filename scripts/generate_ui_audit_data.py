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

templates_dir = os.path.join(settings.BASE_DIR, 'templates')

# Map of views to templates
view_to_template = {}
for mod in [acc_views, ex_views, res_views]:
    import inspect
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        try:
            src = inspect.getsource(obj)
            renders = re.findall(r"render\s*\(\s*request\s*,\s*['\"](.*?)['\"]", src)
            if renders:
                view_to_template[f"{mod.__name__}.{name}"] = renders
        except Exception:
            pass

# Reverse map: template -> views
template_to_views = {}
for v, t_list in view_to_template.items():
    for t in t_list:
        template_to_views.setdefault(t, []).append(v)

# Also inspect all routes
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

# Route to template
route_to_template = {}
template_to_routes = {}
for r in all_routes:
    tmpls = view_to_template.get(r['view'], [])
    r['templates'] = tmpls
    for t in tmpls:
        template_to_routes.setdefault(t, []).append(r)

all_templates = []
for root, dirs, files in os.walk(templates_dir):
    for f in files:
        if f.endswith('.html'):
            rel_path = os.path.relpath(os.path.join(root, f), templates_dir).replace('\\', '/')
            all_templates.append(rel_path)

audit_results = []

for t in sorted(all_templates):
    full_path = os.path.join(templates_dir, t)
    with open(full_path, 'r', encoding='utf-8', errors='ignore') as fp:
        raw = fp.read()
    
    line_count = len(raw.splitlines())
    extends_match = re.search(r'{%\s*extends\s*[\'"](.*?)[\'"]\s*%}', raw)
    extends = extends_match.group(1) if extends_match else None
    
    uses_tailwind = 'cdn.tailwindcss.com' in raw
    uses_google_fonts = 'fonts.googleapis.com' in raw
    
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', raw, re.DOTALL | re.IGNORECASE)
    style_lines = sum(len(b.splitlines()) for b in style_blocks)
    
    # Hex colors
    all_hex = set(re.findall(r'#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})\b', raw))
    
    # Check blue/indigo/purple colors
    blue_colors = [c for c in all_hex if c.lower() in (
        '154ceb', '0036bb', 'edf1fe', '2563eb', '1d4ed8', '3b82f6', '1e40af', '4f46e5', '6366f1', '0d6efd', '0042df', '315efb'
    )]
    
    # Check components
    bento_components = {
        'bento_grid': 'bento-grid' in raw,
        'bento_card': 'bento-card' in raw,
        'bento_btn': 'bento-btn' in raw,
        'bento_badge': 'bento-badge' in raw,
        'bento_table': 'bento-table' in raw,
        'bento_input': any(k in raw for k in ['bento-input', 'bento-select', 'bento-textarea', 'bento-form-group']),
        'bento_stat': 'bento-stat' in raw,
        'bento_alert': 'bento-alert' in raw,
        'bento_empty': 'bento-empty-state' in raw,
    }
    
    legacy_components = {
        'card': bool(re.search(r'\bcard\b', raw)) and not 'bento-card' in raw,
        'btn': bool(re.search(r'\bbtn\b(?!-)', raw)) and not 'bento-btn' in raw,
        'table': '<table' in raw and 'bento-table' not in raw,
    }
    
    # Navigation analysis
    has_custom_sidebar = bool(re.search(r'<aside\b', raw, re.IGNORECASE))
    has_custom_header = bool(re.search(r'<header\b', raw, re.IGNORECASE))
    
    # Determine issues
    issues = []
    
    if t == 'base.html':
        compliance = 'BASELINE'
    elif uses_tailwind:
        compliance = 'INCONSISTENT'
        issues.append({
            'severity': 'Critical',
            'category': 'External CSS Framework / Architecture',
            'rule': 'All pages must inherit base.html and use the centralized design-tokens.css and bento.css',
            'deviation': 'Page is a standalone HTML document importing external Tailwind CDN (cdn.tailwindcss.com)',
            'fix': 'Refactor to extend base.html, remove Tailwind CDN, and convert layout to Bento Grid components'
        })
        issues.append({
            'severity': 'Critical',
            'category': 'Color Palette Inconsistency',
            'rule': 'Official Sage-Green palette: #5C7057 (Primary), #89A482 (Secondary), #ACC5A6 (Light), #D1EDD3 (Mint)',
            'deviation': f'Page overrides palette with Tailwind blue theme: #154ceb, #0036bb, #0042df, #edf1fe ({blue_colors})',
            'fix': 'Replace blue utility classes and tailwind-config with official Sage-Green CSS design tokens'
        })
        if has_custom_sidebar:
            issues.append({
                'severity': 'High',
                'category': 'Navigation Duplication',
                'rule': 'Sidebar navigation is managed centrally in base.html with role-based routing and active states',
                'deviation': 'Duplicates complete sidebar markup independently, causing desynchronization with base.html navigation items',
                'fix': 'Remove duplicate <aside> and let base.html render unified role-based sidebar'
            })
    elif extends is None:
        if t == 'exams/exam_room.html':
            compliance = 'COMPLIANT_SPECIALIZED'
            # Dedicated distraction-free workspace
        else:
            compliance = 'INCONSISTENT'
            issues.append({
                'severity': 'High',
                'category': 'Template Inheritance',
                'rule': 'All standard pages must extend base.html',
                'deviation': 'Standalone HTML document without base template inheritance',
                'fix': 'Refactor to extend base.html'
            })
    else:
        # Extends base.html
        if blue_colors:
            issues.append({
                'severity': 'Medium',
                'category': 'Color Consistency',
                'rule': 'Use Sage-Green color palette and design tokens',
                'deviation': f'Hardcoded conflicting blue colors: {blue_colors}',
                'fix': 'Replace with var(--eps-sage-primary) or related design tokens'
            })
        if style_lines > 40 and t != 'exams/exam_readiness.html':
            issues.append({
                'severity': 'Low',
                'category': 'Inline Stylesheet Bloat',
                'rule': 'Styles should reside in bento.css or design-tokens.css rather than large <style> blocks',
                'deviation': f'{style_lines} lines of inline <style>',
                'fix': 'Move recurring styles into bento.css'
            })
        if legacy_components['table']:
            issues.append({
                'severity': 'Medium',
                'category': 'Unstyled Table',
                'rule': 'Tables should use .bento-table and be wrapped in .bento-table-wrapper for responsive horizontal scrolling',
                'deviation': 'Raw unstyled <table> without Bento wrapper',
                'fix': 'Add class="bento-table" and wrap in <div class="bento-table-wrapper">'
            })
            
        compliance = 'INCONSISTENT' if any(i['severity'] in ('Critical', 'High') for i in issues) else ('COMPLIANT' if not issues else 'PARTIALLY_INCONSISTENT')

    associated_routes = template_to_routes.get(t, [])
    associated_views = template_to_views.get(t, [])

    audit_results.append({
        'template': t,
        'lines': line_count,
        'extends': extends,
        'uses_tailwind': uses_tailwind,
        'uses_google_fonts': uses_google_fonts,
        'style_lines': style_lines,
        'blue_colors': blue_colors,
        'bento_components': bento_components,
        'legacy_components': legacy_components,
        'has_custom_sidebar': has_custom_sidebar,
        'has_custom_header': has_custom_header,
        'compliance': compliance,
        'issues': issues,
        'routes': [r['url'] for r in associated_routes],
        'views': associated_views,
    })

print(f"Total templates audited: {len(audit_results)}")
comp_counts = {}
for a in audit_results:
    comp_counts[a['compliance']] = comp_counts.get(a['compliance'], 0) + 1
print("Compliance summary:", comp_counts)

with open('scripts/ui_audit_data.json', 'w', encoding='utf-8') as out:
    json.dump(audit_results, out, indent=2)

print("Saved detailed report data to scripts/ui_audit_data.json")
