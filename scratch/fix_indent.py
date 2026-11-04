with open('accounts/models.py', 'r', encoding='utf-8') as f:
    text = f.read()

bad_snippet = """        course = models.ForeignKey(
        'Course',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrolled_profiles'
    )"""

fixed_snippet = """    course = models.ForeignKey(
        'Course',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrolled_profiles'
    )"""

assert bad_snippet in text, "bad_snippet not found"
text = text.replace(bad_snippet, fixed_snippet)

with open('accounts/models.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Indentation fixed.")
