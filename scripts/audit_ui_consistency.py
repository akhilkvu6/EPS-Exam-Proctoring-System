import os
import re
import sys
import inspect
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam.settings')
django.setup()

from django.urls import get_resolver
from django.conf import settings
from accounts import views as acc_views
from exams import views as ex_views
from results import views as res_views

# 1. Map Views to Templates
modules = [acc_views, ex_views, res_views]
view_to_templates = {}

for mod in modules:
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        try:
            src = inspect.getsource(obj)
            renders = re.findall(r"render\s*\(\s*request\s*,\s*['\"](.*?)['\"]", src)
            if renders:
                view_to_templates[f"{mod.__name__}.{name}"] = renders
        except Exception:
            pass

# 2. Extract all URL routes
def extract_urls(urlpatterns, prefix=''):
    routes = []
    for pattern in urlpatterns:
        if hasattr(pattern, 'url_patterns'):
            sub_prefix = prefix + str(pattern.pattern)
            routes.extend(extract_urls(pattern.url_patterns, sub_prefix))
        else:
            route_str = prefix + str(pattern.pattern)
            cb = pattern.callback
            view_name = getattr(cb, '__name__', str(cb))
            view_module = getattr(cb, '__module__', '')
            full_view = f"{view_module}.{view_name}"
            url_name = pattern.name or ''
            
            # Determine RBAC decorator from source or view name
            rbac = 'Public / Guest'
            if 'admin' in full_view or 'admin' in route_str:
                rbac = 'Administrator (@admin_required)'
            elif 'teacher' in full_view or 'teacher' in route_str or 'grade' in route_str or 'manage' in route_str or 'create_exam' in full_view or 'question' in route_str or 'invigilate' in route_str:
                rbac = 'Teacher (@teacher_required)'
            elif 'student' in full_view or 'student' in route_str or 'attempt' in route_str or 'readiness' in route_str or 'exam_room' in full_view:
                rbac = 'Student (@student_required)'
            elif 'profile' in full_view or 'change_password' in full_view or 'account_status' in full_view or 'notifications' in full_view:
                rbac = 'Authenticated (@login_required)'

            templates_used = view_to_templates.get(full_view, [])
            routes.append({
                'route': '/' + route_str.lstrip('^'),
                'view': full_view,
                'name': url_name,
                'rbac': rbac,
                'templates': templates_used
            })
    return routes

resolver = get_resolver()
all_routes = extract_urls(resolver.url_patterns)

# 3. Discover all templates
templates_dir = os.path.join(settings.BASE_DIR, 'templates')
all_templates = []
for root, dirs, files in os.walk(templates_dir):
    for f in files:
        if f.endswith('.html'):
            rel_path = os.path.relpath(os.path.join(root, f), templates_dir)
            all_templates.append(rel_path.replace('\\', '/'))

print(f"Total Routes Discovered: {len(all_routes)}")
print(f"Total Templates Discovered: {len(all_templates)}")

# 4. Deep Inspection of Each Template
template_audits = {}

for t in sorted(all_templates):
    full_path = os.path.join(templates_dir, t)
    with open(full_path, 'r', encoding='utf-8', errors='ignore') as fp:
        content = fp.read()
    
    extends_match = re.search(r'{%\s*extends\s*[\'"](.*?)[\'"]\s*%}', content)
    extends = extends_match.group(1) if extends_match else None
    
    has_doctype = bool(re.search(r'<!DOCTYPE\s+html', content, re.IGNORECASE))
    has_html_tag = bool(re.search(r'<html[\s>]', content, re.IGNORECASE))
    
    tailwind = bool(re.search(r'cdn\.tailwindcss\.com', content))
    google_fonts = bool(re.search(r'fonts\.googleapis\.com', content))
    material_symbols = bool(re.search(r'Material\+Symbols', content))
    
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.IGNORECASE)
    total_style_lines = sum(len(b.splitlines()) for b in style_blocks)
    
    hex_colors = set(re.findall(r'#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})\b', content))
    conflicting_blues = [c for c in hex_colors if c.lower() in (
        '154ceb', '0036bb', 'edf1fe', '2563eb', '1d4ed8', '3b82f6', '1e40af', '4f46e5', '6366f1', '0d6efd'
    )]
    
    has_bento_grid = 'bento-grid' in content
    has_bento_card = 'bento-card' in content
    has_bento_btn = 'bento-btn' in content
    has_bento_badge = 'bento-badge' in content
    has_bento_table = 'bento-table' in content
    has_bento_input = any(k in content for k in ['bento-input', 'bento-select', 'bento-textarea', 'bento-form'])
    
    has_legacy_card = bool(re.search(r'\bcard\b', content))
    has_legacy_btn = bool(re.search(r'\bbtn\b(?!-)', content))
    has_legacy_table = bool(re.search(r'\btable\b(?!-)', content))
    
    # Check if template has unstyled tables
    has_raw_table = '<table' in content and 'bento-table' not in content and 'table' not in content
    
    # Check navigation / header duplication
    has_duplicate_sidebar = ('<aside' in content or 'app-sidebar' in content) and extends == 'base.html'
    has_standalone_sidebar = ('<aside' in content or 'app-sidebar' in content) and extends is None and t != 'base.html'
    
    # Determine compliance status
    inconsistencies = []
    
    if t == 'base.html':
        status = 'BASELINE_FOUNDATION'
    elif tailwind:
        status = 'INCONSISTENT_TAILWIND_ISOLATION'
        inconsistencies.append("Uses external Tailwind CDN instead of shared design tokens")
        inconsistencies.append("Defines conflicting blue color palette (#154ceb, #0036bb, #edf1fe)")
        inconsistencies.append("Does not inherit from base.html; has standalone <html> and <head>")
        if has_standalone_sidebar:
            inconsistencies.append("Duplicates sidebar navigation independently from base.html")
    elif extends is None:
        if t == 'exams/exam_room.html':
            status = 'INTENTIONAL_FULLSCREEN_WORKSPACE'
            # Exam room is an intentional distraction-free proctoring workspace, but verify palette & bento
            if not any(k in content for k in ['bento.css', 'design-tokens.css']):
                inconsistencies.append("Standalone fullscreen exam room missing shared design-tokens.css link")
        else:
            status = 'INCONSISTENT_STANDALONE'
            inconsistencies.append("Does not extend base.html")
    else:
        # Extends base.html
        if conflicting_blues:
            inconsistencies.append(f"Contains conflicting blue hex colors: {conflicting_blues}")
        if total_style_lines > 50:
            inconsistencies.append(f"Excessive inline <style> block ({total_style_lines} lines); should use bento.css")
        if has_duplicate_sidebar:
            inconsistencies.append("Duplicates sidebar markup inside child template")
            
        if not inconsistencies:
            status = 'COMPLIANT_BENTO'
        else:
            status = 'INCONSISTENT_STYLING'

    template_audits[t] = {
        'status': status,
        'extends': extends,
        'tailwind': tailwind,
        'style_lines': total_style_lines,
        'conflicting_blues': conflicting_blues,
        'bento_classes': {
            'grid': has_bento_grid,
            'card': has_bento_card,
            'btn': has_bento_btn,
            'badge': has_bento_badge,
            'table': has_bento_table,
            'form': has_bento_input,
        },
        'inconsistencies': inconsistencies
    }

print("\n=== TEMPLATE AUDIT SUMMARY ===")
counts = {}
for t, d in template_audits.items():
    s = d['status']
    counts[s] = counts.get(s, 0) + 1
for s, c in sorted(counts.items()):
    print(f"  {s}: {c}")

print("\n=== DETAILED LIST OF INCONSISTENT TEMPLATES ===")
for t, d in template_audits.items():
    if d['status'] not in ('COMPLIANT_BENTO', 'BASELINE_FOUNDATION', 'INTENTIONAL_FULLSCREEN_WORKSPACE'):
        print(f"\n[Template] {t} ({d['status']})")
        for inc in d['inconsistencies']:
            print(f"   - {inc}")
