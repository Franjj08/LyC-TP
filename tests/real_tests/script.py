import os
import subprocess
import sys

LOX_BINARY = sys.argv[1].split() if len(sys.argv) > 1 else ["plox"]

currentdir = os.path.dirname(os.path.abspath(__file__))

for lox_file in filter(lambda f: f.endswith(".lox"), sorted(os.listdir(currentdir))):
    print(f"$ {' '.join(LOX_BINARY)} tests/real_tests/{lox_file}")

    result = subprocess.run(
        [*LOX_BINARY, os.path.join(currentdir, lox_file)],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )

    out = result.stdout.strip()
    error_output = result.stderr.strip()
    print(out)
    if error_output:
        print(error_output, file=sys.stderr)
    print()

    if result.returncode != 0 or "error" in out.lower() or "error" in error_output.lower():
        print(" -------- ")
        print("|  ERROR  |")
        print(" -------- ")
        sys.exit(1)

print(" -------- ")
print("| Todo OK |")
print(" -------- ")
