import pathlib

q = pathlib.Path('docs/AUTONOMOUS_QUEUE.md')
lines = q.read_text(encoding='utf-8').splitlines(keepends=True)
out, changed = [], 0
for line in lines:
    if line.startswith('| Q-61 |'):
        cells = line.rstrip('\n').split('|')
        # Repair: the title had been overwritten by the gate text in an earlier edit.
        cells[2] = " Installer crashes intermittently at startup even with the software-rendering wrapper "
        cells[3] = (" 10 installer starts in a row without a crash, or a documented cause ")
        line = '|'.join(cells) + '\n'
        changed += 1
    out.append(line)
q.write_text(''.join(out), encoding='utf-8')
print('rows repaired:', changed)
