import unittest
import sys
import os

print("="*60)
print("PHASE 1A & 1B ENGINEERING AUDIT")
print("="*60)

# Check tests
import subprocess

print("\n1. Running Phase 1A Validation...")
res1 = subprocess.run([sys.executable, "-m", "unittest", "scratch/test_atmosphere.py"], capture_output=True, text=True)
if res1.returncode == 0:
    print("PASS: Atmosphere Model (Phase 1A)")
else:
    print("FAIL: Atmosphere Model")
    print(res1.stderr)

print("\n2. Running Phase 1B Validation...")
res2 = subprocess.run([sys.executable, "-m", "unittest", "scratch/test_turbo_intake.py"], capture_output=True, text=True)
if res2.returncode == 0:
    print("PASS: Turbo Intake Model (Phase 1B)")
else:
    print("FAIL: Turbo Intake Model")
    print(res2.stderr)

print("\n3. Validating Rule Compliance...")
docs_path = os.path.join(os.path.dirname(__file__), "..", "docs", "physics", "1B_turbo_intake")
impl_notes = os.path.join(docs_path, "implementation_notes.md")

if os.path.exists(impl_notes):
    print("PASS: implementation_notes.md exists.")
else:
    print("FAIL: implementation_notes.md missing.")

registry = os.path.join(os.path.dirname(__file__), "..", "docs", "PHYSICS_FORMULA_REGISTRY.txt")
if os.path.exists(registry):
    with open(registry, 'r') as f:
        content = f.read()
        if 'ATM-00' in content:
            print("PASS: ATM-00 Geopotential formula documented in registry.")
        else:
            print("FAIL: ATM-00 missing from registry.")
else:
    print("FAIL: PHYSICS_FORMULA_REGISTRY.txt missing.")

print("\nAUDIT COMPLETE.")
if res1.returncode == 0 and res2.returncode == 0 and os.path.exists(impl_notes) and 'ATM-00' in content:
    print("STATUS: APPROVED FOR PHASE 1C.")
else:
    print("STATUS: PENDING FIXES.")
