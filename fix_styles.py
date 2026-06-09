import os, glob, re

import os
current_dir = os.path.dirname(os.path.abspath(__file__))
d = os.path.join(current_dir, 'logger_app', 'ui')

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'setStyleSheet' in line and not '{' in line and not 'transparent' in line:
            m = re.search(r'([a-zA-Z0-9_.]+)\.setStyleSheet\(([\"\'\\])(.*?)([\"\'\\])\)', line)
            if m:
                var_name = m.group(1)
                quote = m.group(2)
                style = m.group(3)
                
                cls = 'QWidget'
                if 'frame' in var_name or 'sec' in var_name or 'ctrl' in var_name or var_name in ['left', 'right', 'right_panel', 'right_sidebar', 'hwid_box']:
                    cls = 'QFrame'
                if 'stack' in var_name:
                    cls = 'QStackedWidget'
                
                new_style = f'.{cls} {{ {style.replace("background:", "background-color:")} }}'
                new_line = line.replace(f'{quote}{style}{quote}', f'{quote}{new_style}{quote}')
                lines[i] = new_line
                print(f'Replaced in {os.path.basename(filepath)}: {new_line.strip()}')
                
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

for f in glob.glob(d + '/*.py'):
    process_file(f)
