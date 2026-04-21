import os

file_path = 'dictation.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Fonts
content = content.replace('"Segoe UI"', '"Helvetica Neue"')
content = content.replace("'Segoe UI'", "'Helvetica Neue'")

# We want the UI to aggressively show exactly the aesthetic we promised.
# Replacing border with neon glowing border for active cards
content = content.replace('highlightbackground=BORDER,', 'highlightbackground="#30d158",')
# Change some text sizes if "bold" is not well supported
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished patching fonts and borders")
