"""Shared accuracy / confusion-matrix reporting for routing evals."""
from collections import Counter


def summarize(results: list, labels: list) -> dict:
    total = len(results)
    correct = sum(1 for r in results if r['correct'])
    accuracy = correct / total if total else 0.0

    by_difficulty = {}
    for difficulty in sorted({r['difficulty'] for r in results}):
        subset = [r for r in results if r['difficulty'] == difficulty]
        sub_correct = sum(1 for r in subset if r['correct'])
        by_difficulty[difficulty] = {
            'total': len(subset),
            'correct': sub_correct,
            'accuracy': sub_correct / len(subset) if subset else 0.0,
        }

    confusion = {expected: Counter() for expected in labels}
    for r in results:
        if r['expected'] in confusion:
            confusion[r['expected']][r['actual']] += 1

    flaky = [r['id'] for r in results if r['flaky']]

    return {
        'total': total,
        'correct': correct,
        'accuracy': accuracy,
        'by_difficulty': by_difficulty,
        'confusion': confusion,
        'flaky': flaky,
    }


def print_report(title: str, results: list, labels: list):
    summary = summarize(results, labels)

    print(f"\n{'=' * 78}")
    print(title)
    print('=' * 78)
    print(f"Overall accuracy: {summary['correct']}/{summary['total']} ({summary['accuracy'] * 100:.1f}%)")

    print("\nBy difficulty:")
    for difficulty, stats in summary['by_difficulty'].items():
        print(f"  {difficulty:8s} {stats['correct']}/{stats['total']} ({stats['accuracy'] * 100:.1f}%)")

    print("\nConfusion matrix (rows = expected, cols = actual):")
    header = ' ' * 14 + ''.join(f'{str(label):>12}' for label in labels)
    print(header)
    for expected in labels:
        row = summary['confusion'].get(expected, Counter())
        counts = ''.join(f'{row.get(label, 0):>12}' for label in labels)
        print(f'{str(expected):>14}{counts}')

    if summary['flaky']:
        print(f"\nFlaky cases (repeated attempts disagreed): {', '.join(summary['flaky'])}")

    failures = [r for r in results if not r['correct']]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for r in failures:
            print(f"  [{r['id']}] expected={r['expected']!r} actual={r['actual']!r} attempts={r['attempts']}")
            print(f"          input: {r['input']!r}")
    print()
