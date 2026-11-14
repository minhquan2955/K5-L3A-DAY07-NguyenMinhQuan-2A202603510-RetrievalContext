"""Day07 CLI: check the Day06 store, search, or ask the real agent."""
import argparse
import importlib.metadata
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agentic import run_agent
from model_controller import OpenAIController
from retrieval import Day6Retriever


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'search', 'ask'))
    parser.add_argument('--env-file', type=Path, default=Path('.env'))
    parser.add_argument('--method', choices=('dense', 'tfidf', 'hybrid'), default='dense')
    parser.add_argument('--strategy', default='B')
    parser.add_argument('--model', help='Agent model; default AGENT_MODEL or gpt-6-luna')
    parser.add_argument('--embedding-model', help='Must match the Day06 document embedding model')
    parser.add_argument('--dimensions', type=int, default=1536)
    parser.add_argument('--query')
    parser.add_argument('--filter', default='{}', help='JSON metadata filter supplied by the user')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--candidate-k', type=int, default=20)
    parser.add_argument('--budget', type=int, default=4000, help='Final context budget in characters, including citations')
    parser.add_argument('--max-searches', type=int, default=3)
    parser.add_argument('--output', type=Path, help='New trace JSON file; existing files are never overwritten')
    args = parser.parse_args(argv)
    if args.command != 'check' and (not args.query or not args.query.strip()):
        parser.error('--query is required for search and ask')
    if min(args.top_k, args.candidate_k, args.budget, args.max_searches, args.dimensions) < 1:
        parser.error('All numeric limits must be positive')
    output = args.output or Path('starter/results/smoke') / f'{args.command}-{uuid4().hex}.json'
    if output.exists():
        parser.error('Output already exists; use a new path')
    started = time.perf_counter()
    retriever = controller = None
    trace = {'created_at': datetime.now(timezone.utc).isoformat(), 'command': args.command,
             'purpose': 'interactive_smoke_not_benchmark', 'question': args.query,
             'config': {'method': args.method, 'strategy': args.strategy, 'top_k': args.top_k,
                        'candidate_k': args.candidate_k, 'budget_chars': args.budget,
                        'max_searches': args.max_searches, 'dimensions': args.dimensions},
             'cost_usd': None, 'cost_note': 'Not priced; token usage is measured separately. No cost is invented.'}
    try:
        from dotenv import load_dotenv
        if not args.env_file.is_file():
            raise ValueError('Environment file is missing; supply --env-file')
        # Explicit env file is authoritative for this run; do not print its values.
        load_dotenv(args.env_file, override=True)
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError('DATABASE_URL is required')
        filters = json.loads(args.filter)
        if not isinstance(filters, dict):
            raise ValueError('filter must be a JSON object')
        model = args.model or os.environ.get('AGENT_MODEL') or 'gpt-6-luna'
        embedding_model = args.embedding_model or os.environ.get('EMBEDDING_MODEL') or 'text-embedding-3-small'
        trace['config'].update({'agent_model': model, 'embedding_model': embedding_model, 'filter': filters})
        trace['packages'] = {name: importlib.metadata.version(name) for name in ('openai', 'psycopg', 'python-dotenv')}
        trace['python'] = sys.version.split()[0]
        retriever = Day6Retriever(database_url, method=args.method, strategy=args.strategy,
                                 embedding_model=embedding_model, dimensions=args.dimensions,
                                 candidate_k=args.candidate_k)
        trace['corpus'] = {'table': 'public.day6_chunks', 'strategy': args.strategy,
                           'chunks': len(retriever.chunks), 'run_fingerprint': retriever.fingerprint,
                           'sources': sorted({c['source'] for c in retriever.chunks}),
                           'page_numbering': 'physical PDF page, 1-based'}
        if args.command == 'check':
            trace['status'] = 'ok'
        elif args.command == 'search':
            trace.update({'status': 'ok', 'results': retriever.search(args.query, filters=filters, top_k=args.top_k)})
        else:
            from openai import OpenAI
            controller = OpenAIController(OpenAI(timeout=45, max_retries=1), model)
            trace.update(run_agent(args.query, controller, retriever, filters=filters,
                                   top_k=args.top_k, budget=args.budget, max_searches=args.max_searches,
                                   events=trace.setdefault('events', [])))
    except Exception as exc:
        # Exception messages from providers/drivers can contain credential fragments.
        trace.update({'status': 'error', 'error': {'type': type(exc).__name__}})
        status_code = getattr(exc, 'status_code', None)
        if isinstance(status_code, int):
            trace['error']['http_status'] = status_code
    finally:
        trace['elapsed_ms'] = (time.perf_counter() - started) * 1000
        trace['retrieval_calls'] = retriever.calls if retriever else []
        trace['embedding_usage'] = retriever.embedding_usage if retriever else []
        trace['model_calls'] = controller.calls if controller else []
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as file:
            json.dump(trace, file, ensure_ascii=False, indent=2)
            file.write('\n')
    print(json.dumps({'status': trace['status'], 'trace': str(output),
                      **{key: trace[key] for key in ('answer', 'error', 'corpus') if key in trace}},
                     ensure_ascii=False, indent=2))
    return 1 if trace['status'] == 'error' else 0


if __name__ == '__main__':
    raise SystemExit(main())
