#!/usr/bin/env python3
"""Routing-accuracy eval for two routing decisions in the LangGraph agent:

  orchestrator -> home_repair   (nodes/orchestrator.py's classify_intent)
  home_repair  -> check_result  (nodes/home_repair.py's decide_search)

The home_repair -> check_result handoff in production is actually gated by three
things: the should_search decision, the search itself returning results, and the
contextual grounding guardrail passing. Only the first is a routing *classification*
in the same sense as orchestrator's intent routing — the other two are search-quality
and guardrail concerns, already covered separately (see the guardrail smoke test).
So this eval scopes "home_repair -> check_result" to should_search accuracy only.

This hits real Amazon Bedrock (Nova) via the actual node code — it costs money and
takes time, so it's not part of the fast pytest suite or CI. Run it manually:

    pip install -r evals/requirements.txt
    pip install -r lambdas/langgraph-agent/requirements.txt
    python evals/routing/run_routing_eval.py --dataset orchestrator_intent
    python evals/routing/run_routing_eval.py --dataset home_repair_search_decision
    python evals/routing/run_routing_eval.py --dataset all --repeats 5

Needs AWS credentials with bedrock:InvokeModel access to the configured model
(BEDROCK_MODEL_ID env var, defaults to amazon.nova-pro-v1:0) in us-east-1.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / 'lambdas' / 'langgraph-agent'))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402

from nodes.home_repair import _SYSTEM, decide_search  # noqa: E402
from nodes.orchestrator import classify_intent  # noqa: E402

from report import print_report  # noqa: E402

DATASETS_DIR = Path(__file__).resolve().parent / 'datasets'


def _load_dataset(name: str) -> list:
    with open(DATASETS_DIR / f'{name}.yaml') as f:
        return yaml.safe_load(f)


def _build_lc_messages(history: list) -> list:
    """Mirrors home_repair_node's message construction exactly (system prompt +
    every turn as Human/AIMessage) so decide_search sees what it would in production."""
    lc_messages = [SystemMessage(content=_SYSTEM)]
    for turn in history:
        if turn['role'] == 'user':
            lc_messages.append(HumanMessage(content=turn['content']))
        elif turn['role'] == 'assistant':
            lc_messages.append(AIMessage(content=turn['content']))
    return lc_messages


def _summarize_history(history: list) -> str:
    return ' / '.join(f"{t['role']}: {t['content']}" for t in history)


def run_orchestrator_intent(repeats: int) -> list:
    results = []
    for case in _load_dataset('orchestrator_intent'):
        attempts = [classify_intent(case['input']) for _ in range(repeats)]
        actual = Counter(attempts).most_common(1)[0][0]
        results.append({
            'id': case['id'],
            'input': case['input'],
            'expected': case['expected'],
            'actual': actual,
            'attempts': attempts,
            'correct': actual == case['expected'],
            'flaky': len(set(attempts)) > 1,
            'difficulty': case.get('difficulty', 'easy'),
        })
    return results


def run_home_repair_search_decision(repeats: int) -> list:
    results = []
    for case in _load_dataset('home_repair_search_decision'):
        lc_messages = _build_lc_messages(case['history'])
        attempts = [
            bool(decide_search(lc_messages, session_id=f"eval-{case['id']}").get('should_search'))
            for _ in range(repeats)
        ]
        actual = Counter(attempts).most_common(1)[0][0]
        results.append({
            'id': case['id'],
            'input': _summarize_history(case['history']),
            'expected': case['expected_should_search'],
            'actual': actual,
            'attempts': attempts,
            'correct': actual == case['expected_should_search'],
            'flaky': len(set(attempts)) > 1,
            'difficulty': case.get('difficulty', 'easy'),
        })
    return results


RUNNERS = {
    'orchestrator_intent': (
        'orchestrator -> home_repair (intent routing)',
        run_orchestrator_intent,
        ['QUESTION', 'PROJECT', 'IRRELEVANT'],
    ),
    'home_repair_search_decision': (
        'home_repair -> check_result (should_search decision)',
        run_home_repair_search_decision,
        [True, False],
    ),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset', choices=[*RUNNERS.keys(), 'all'], default='all')
    parser.add_argument('--repeats', type=int, default=3, help='Repeat each case N times to detect flakiness')
    args = parser.parse_args()

    names = list(RUNNERS.keys()) if args.dataset == 'all' else [args.dataset]
    for name in names:
        title, runner, labels = RUNNERS[name]
        results = runner(args.repeats)
        print_report(title, results, labels)


if __name__ == '__main__':
    main()
