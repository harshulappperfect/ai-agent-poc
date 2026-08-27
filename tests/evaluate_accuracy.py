import sys
import subprocess
import re
import time

def calculate_accuracy():
    test_suite = {
        "Date Conversion": "tests/test_financial_year.py",
        "Database Tools": "tests/test_tools.py",
        "Agent Config": "tests/test_agent.py",
        "MCP Protocol": "tests/test_mcp_agent.py",
    }
    
    total_passed = 0
    total_failed = 0
    start_time = time.time()

    print("=" * 60)
    print("         ACCURACY METRICS REPORT")
    print("=" * 60)

    for category_name, file_path in test_suite.items():
        # 1. Run pytest command
        cmd = [sys.executable, "-m", "pytest", file_path, "-q"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        output = res.stdout + res.stderr

        # 2. Extract passed and failed counts
        p_match = re.search(r"(\d+)\s+passed", output)
        f_match = re.search(r"(\d+)\s+failed", output)

        passed = int(p_match.group(1)) if p_match else 0
        failed = int(f_match.group(1)) if f_match else 0
        cat_total = passed + failed

        # 3. Calculate category accuracy
        acc = (passed / cat_total * 100) if cat_total > 0 else 100.0

        total_passed += passed
        total_failed += failed

        print(f"{category_name:<25} | Passed: {passed:<3} | Failed: {failed:<3} | Accuracy: {acc:.1f}%")

    # 4. Calculate overall metric
    grand_total = total_passed + total_failed
    overall_acc = (total_passed / grand_total * 100) if grand_total > 0 else 0.0
    elapsed = time.time() - start_time

    print("-" * 60)
    print(f"OVERALL ACCURACY METRIC   | Passed: {total_passed:<3} | Failed: {total_failed:<3} | Accuracy: {overall_acc:.1f}%")
    print("=" * 60)
    print(f"Execution Time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    calculate_accuracy()
