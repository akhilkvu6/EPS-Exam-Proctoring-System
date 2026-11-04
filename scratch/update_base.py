with open('templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace header block
old_header = """    {% else %}
        <!-- Public Guest Header -->
        <header class="public-header" style="background-color: var(--bg-surface); border-bottom: 1px solid var(--border-subtle); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);">
            <div class="public-header__container" style="max-width: 1200px; margin: 0 auto; padding: 0 var(--space-6); height: 64px; display: flex; align-items: center; justify-content: space-between;">
                <a href="{% url 'home' %}" class="nav-brand" style="display: flex; align-items: center; gap: var(--space-3); text-decoration: none;">
                    <span class="brand-badge" style="width: 34px; height: 34px; border-radius: 9px; background: var(--text-primary); color: var(--text-inverse); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; letter-spacing: 0.04em; box-shadow: 0 2px 8px rgba(0,0,0,0.12);">EPS</span>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-weight: 700; font-size: var(--font-size-base); color: var(--text-primary); letter-spacing: -0.01em;">Examination Portal</span>
                        <span style="font-size: 10px; font-weight: 700; background: rgba(16, 185, 129, 0.1); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.25); padding: 2px 7px; border-radius: 9999px; display: inline-flex; align-items: center; gap: 4px;">
                            <span style="width: 5px; height: 5px; border-radius: 50%; background: #10B981;"></span>
                            Online
                        </span>
                    </div>
                </a>

                <nav style="display: flex; align-items: center; gap: var(--space-3);">
                    <button type="button" class="theme-toggle-btn btn btn-ghost btn-sm" title="Toggle Theme" aria-label="Toggle light/dark theme" style="padding: 7px 10px; border-radius: var(--radius-control); display: flex; align-items: center; justify-content: center;">
                        <i data-lucide="sun-moon" class="lucide-icon icon-sm"></i>
                    </button>
                    <a href="{% url 'common_login' %}" class="btn btn-secondary btn-sm" style="padding: 0.45rem 1rem; font-weight: 600; border-radius: var(--radius-control);">Sign In</a>
                    <a href="{% url 'register' %}" class="btn btn-primary btn-sm" style="padding: 0.45rem 1.1rem; font-weight: 600; border-radius: var(--radius-control); box-shadow: 0 2px 8px rgba(0,0,0,0.1);">Get Started</a>
                </nav>
            </div>
        </header>
    {% endif %}"""

new_header = """    {% else %}
        {% block public_header %}
        <!-- Public Guest Header -->
        <header class="public-header" style="background-color: var(--bg-surface); border-bottom: 1px solid var(--border-subtle); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);">
            <div class="public-header__container" style="max-width: 1200px; margin: 0 auto; padding: 0 var(--space-6); height: 64px; display: flex; align-items: center; justify-content: space-between;">
                <a href="{% url 'home' %}" class="nav-brand" style="display: flex; align-items: center; gap: var(--space-3); text-decoration: none;">
                    <span class="brand-badge" style="width: 34px; height: 34px; border-radius: 9px; background: var(--text-primary); color: var(--text-inverse); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; letter-spacing: 0.04em; box-shadow: 0 2px 8px rgba(0,0,0,0.12);">EPS</span>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-weight: 700; font-size: var(--font-size-base); color: var(--text-primary); letter-spacing: -0.01em;">Examination Portal</span>
                        <span style="font-size: 10px; font-weight: 700; background: rgba(16, 185, 129, 0.1); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.25); padding: 2px 7px; border-radius: 9999px; display: inline-flex; align-items: center; gap: 4px;">
                            <span style="width: 5px; height: 5px; border-radius: 50%; background: #10B981;"></span>
                            Online
                        </span>
                    </div>
                </a>

                <nav style="display: flex; align-items: center; gap: var(--space-3);">
                    <button type="button" class="theme-toggle-btn btn btn-ghost btn-sm" title="Toggle Theme" aria-label="Toggle light/dark theme" style="padding: 7px 10px; border-radius: var(--radius-control); display: flex; align-items: center; justify-content: center;">
                        <i data-lucide="sun-moon" class="lucide-icon icon-sm"></i>
                    </button>
                    <a href="{% url 'common_login' %}" class="btn btn-secondary btn-sm" style="padding: 0.45rem 1rem; font-weight: 600; border-radius: var(--radius-control);">Sign In</a>
                    <a href="{% url 'register' %}" class="btn btn-primary btn-sm" style="padding: 0.45rem 1.1rem; font-weight: 600; border-radius: var(--radius-control); box-shadow: 0 2px 8px rgba(0,0,0,0.1);">Get Started</a>
                </nav>
            </div>
        </header>
        {% endblock %}
    {% endif %}"""

old_main = '<main class="app-content" {% if not request.user.is_authenticated %}style="padding-top: var(--space-8);"{% endif %}>'
new_main = '<main class="app-content" {% if request.resolver_match.url_name == \'home\' %}style="padding: 0; max-width: 100%; width: 100%; margin: 0;"{% elif not request.user.is_authenticated %}style="padding-top: var(--space-8);"{% endif %}>'

old_footer = """    <!-- Minimal Public Footer -->
    <footer class="footer" style="padding: var(--space-6) var(--space-4); text-align: center; border-top: 1px solid var(--border-subtle); background-color: var(--bg-surface); color: var(--text-muted); font-size: var(--font-size-xs); transition: background-color var(--transition-normal);">
        <p style="margin: 0; line-height: 1.5;">EPS &mdash; Examination Proctoring System &bull; &copy; 2026 All rights reserved.</p>
    </footer>"""

new_footer = """    {% block footer %}
    <!-- Minimal Public Footer -->
    <footer class="footer" style="padding: var(--space-6) var(--space-4); text-align: center; border-top: 1px solid var(--border-subtle); background-color: var(--bg-surface); color: var(--text-muted); font-size: var(--font-size-xs); transition: background-color var(--transition-normal);">
        <p style="margin: 0; line-height: 1.5;">EPS &mdash; Examination Proctoring System &bull; &copy; 2026 All rights reserved.</p>
    </footer>
    {% endblock %}"""

content_normalized = content.replace('\r\n', '\n')
old_header_norm = old_header.replace('\r\n', '\n')
new_header_norm = new_header.replace('\r\n', '\n')
old_footer_norm = old_footer.replace('\r\n', '\n')
new_footer_norm = new_footer.replace('\r\n', '\n')

assert old_header_norm in content_normalized, "Header not found!"
assert old_main in content_normalized, "Main not found!"
assert old_footer_norm in content_normalized, "Footer not found!"

content_normalized = content_normalized.replace(old_header_norm, new_header_norm)
content_normalized = content_normalized.replace(old_main, new_main)
content_normalized = content_normalized.replace(old_footer_norm, new_footer_norm)

with open('templates/base.html', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(content_normalized)

print('base.html updated successfully!')
