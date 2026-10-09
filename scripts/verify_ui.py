with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

checks = [
    'id="sec-controls"',
    'id="nav-controls"',
    'syncControlsPageUI',
    'cpageJogRing',
    'cpageJogNeedle',
    'startCustomSweep',
    'zeroCalibrateNow',
    'setAcsSensitivity',
    'updateVirtualBmsWatchdog',
    'cpageMotorAmps',
]

all_ok = True
for c in checks:
    present = c in text
    print(f"[{'PASS' if present else 'FAIL'}] Check: {c}")
    if not present:
        all_ok = False

if all_ok:
    print("\nALL UI CHECKS PASSED PERFECTLY!")
else:
    print("\nSOME CHECKS FAILED!")
