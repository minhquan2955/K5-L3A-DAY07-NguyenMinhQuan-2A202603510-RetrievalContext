"""Frozen Day07 benchmark: dev experiments, locked selection, then held-out test."""
import argparse
import hashlib
import json
import os
import statistics
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from agentic import run_agent
from agent_metrics import aggregate
from model_controller import OpenAIController
from retrieval import Day6Retriever

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as file:
        json.dump(obj, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write('\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(cases_path, configs_path):
    paths = [cases_path, configs_path, ROOT/'data/day06_reference.json', *[ROOT/'starter'/name for name in
             ('benchmark.py','baseline.py','agentic.py','retrieval.py','model_controller.py')]]
    return {str(Path(path).resolve().relative_to(ROOT).as_posix()): digest(path) for path in paths}


def agent_input(case):
    return case['question'], case.get('filter', {})


def norm(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def evidence_hit(row, gold):
    return any(row['source_id'] == g['source_id'] and row['page'] == g['page']
               and norm(g['evidence']) in norm(row['text']) for g in gold)


def summarize_retrieval(cases, traces):
    by_id = {t['query_id']: t for t in traces}
    out = {name: {'n':0,'N':0} for name in
           ('original_hit1','original_hit3','first_tool_hit1','first_tool_hit3','context_evidence')}
    out['provider_errors'] = sum(t['status'] == 'error' for t in traces)
    out['original_retrieval_errors'] = sum(t.get('original_retrieval',{}).get('status') == 'error' for t in traces)
    for case in cases:
        if not case['answerable']:
            continue
        trace = by_id[case['id']]
        searches = [e for e in trace.get('events',[]) if e['event'] == 'search']
        original = trace.get('original_retrieval',{}).get('results',[])
        first = searches[0]['results'] if searches else []
        last = searches[-1] if searches else {}
        all_rows = {r['id']:r for e in searches for r in e['results']}
        context = [all_rows[cid] for cid in last.get('context_ids',[]) if cid in all_rows]
        for name, rows in [('original_hit1',original[:1]),('original_hit3',original[:3]),
                           ('first_tool_hit1',first[:1]),('first_tool_hit3',first[:3]),
                           ('context_evidence',context)]:
            out[name]['N'] += 1
            out[name]['n'] += any(evidence_hit(row,case['gold']) for row in rows)
    out['model_prompt_tokens'] = sum(c.get('usage',{}).get('prompt_tokens',0) for t in traces for c in t.get('model_calls',[]))
    out['model_completion_tokens'] = sum(c.get('usage',{}).get('completion_tokens',0) for t in traces for c in t.get('model_calls',[]))
    out['embedding_tokens'] = sum(c['total_tokens'] for t in traces for c in t.get('embedding_usage',[]))
    out['total_tokens'] = out['model_prompt_tokens'] + out['model_completion_tokens'] + out['embedding_tokens']
    out['median_ms'] = statistics.median(t['elapsed_ms'] for t in traces)
    out['search_count_distribution'] = {str(n):sum(sum(e['event']=='search' for e in t.get('events',[]))==n for t in traces)
                                        for n in sorted({sum(e['event']=='search' for e in t.get('events',[])) for t in traces})}
    out['cost_usd'] = None
    out['cost_note'] = 'Unpriced; measured token usage is reported, not an invented USD estimate.'
    return out


def choose_config(summaries):
    return min(summaries, key=lambda s: (-s['context_evidence']['n'], -s['first_tool_hit3']['n'],
                                       s['provider_errors'] + s.get('original_retrieval_errors',0),
                                       s['total_tokens'], s['config_id']))['config_id']


def run_case(case, config, model, database_url, embedding_model):
    from openai import OpenAI
    started = time.perf_counter()
    retriever = controller = None
    question, filters = agent_input(case)
    trace = {'query_id':case['id'],'split':case['split'],'question':question,'config':config,
             'agent_model':model,'created_at':datetime.now(timezone.utc).isoformat(), 'events':[], 'citations':[]}
    try:
        client = OpenAI(timeout=45, max_retries=1)
        retriever = Day6Retriever(database_url, method=config['method'], embedding_model=embedding_model,
                                 candidate_k=config['candidate_k'],client=client)
        trace['corpus'] = {'strategy':'B','chunks':len(retriever.chunks),'run_fingerprint':retriever.fingerprint,
                           'embedding_model':embedding_model,'dimensions':1536}
        reference = read(ROOT/'data/day06_reference.json')
        if retriever.fingerprint != reference['run_fingerprint'] or len(retriever.chunks) != reference['chunk_count']:
            raise ValueError('Database differs from the frozen Day06 reference')
        try:
            rows = retriever.search(question,filters=filters,top_k=max(3,config['top_k']))
            trace['original_retrieval'] = {'status':'ok','query':question,'filter':filters,'results':rows}
        except Exception as exc:
            trace['original_retrieval'] = {'status':'error','error_type':type(exc).__name__}
        controller = OpenAIController(client,model)
        trace.update(run_agent(question,controller,retriever,filters=filters,top_k=config['top_k'],
                               budget=config['budget'],max_searches=config['max_searches'],events=trace['events']))
    except Exception as exc:
        trace.update({'status':'error','error':{'type':type(exc).__name__}})
        if isinstance(getattr(exc,'status_code',None),int):
            trace['error']['http_status'] = exc.status_code
    trace.update({'elapsed_ms':(time.perf_counter()-started)*1000,
                  'model_calls':controller.calls if controller else [],
                  'retrieval_calls':retriever.calls if retriever else [],
                  'embedding_usage':retriever.embedding_usage if retriever else [],'cost_usd':None})
    return trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('run','select','summarize'))
    parser.add_argument('--split',choices=('dev','test'),default='dev')
    parser.add_argument('--env-file',type=Path,default=ROOT/'.env')
    parser.add_argument('--cases',type=Path,default=ROOT/'benchmark/cases.json')
    parser.add_argument('--configs',type=Path,default=ROOT/'benchmark/configs.json')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/day07/run-01')
    parser.add_argument('--workers',type=int,default=4)
    args = parser.parse_args()
    cases, configs = read(args.cases), read(args.configs)
    frozen = read(ROOT/'benchmark/freeze.json')
    # Freeze schema intentionally accepts only the actual file checksum field.
    expected = frozen.get('cases_sha256') or frozen.get('files',{}).get('benchmark/cases.json')
    if expected != digest(args.cases):
        raise ValueError('Benchmark cases differ from freeze')
    current = identity(args.cases,args.configs)
    meta_path = args.output/'metadata.json'
    if args.command=='run':
        from dotenv import load_dotenv
        if not args.env_file.is_file() or args.workers < 1:
            parser.error('An existing env file and positive worker count are required')
        load_dotenv(args.env_file,override=True)
        database_url = os.environ['DATABASE_URL']
        model = os.getenv('AGENT_MODEL') or 'gpt-6-luna'
        embedding_model = os.getenv('EMBEDDING_MODEL') or 'text-embedding-3-small'
        metadata = {'identity':current,'agent_model':model,'embedding_model':embedding_model}
        if meta_path.exists():
            if read(meta_path)!=metadata:
                raise ValueError('Run code/config/model changed; use a new output directory')
        else:
            if args.split=='test':
                raise ValueError('Test requires an existing dev run and selection')
            write_new(meta_path,metadata)
        if args.split=='test':
            selection = read(args.output/'selection.dev.json')
            if selection['identity']!=current or selection['agent_model']!=model:
                raise ValueError('Selection does not match current pipeline')
            ids = {'dense-baseline',selection['selected_config']}
            configs = [c for c in configs if c['id'] in ids]
        elif (args.output/'selection.dev.json').exists():
            raise ValueError('Dev is locked after selection; use a new run for new experiments')
        selected = [c for c in cases if c['split']==args.split]
        futures = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for config in configs:
                for case in selected:
                    path = args.output/args.split/config['id']/(case['id']+'.json')
                    if path.exists():
                        continue  # Resume completed cases including errors; do not silently replace failures.
                    futures[pool.submit(run_case,case,config,model,database_url,embedding_model)] = path
            for future in as_completed(futures):
                path = futures[future]
                trace = future.result()
                write_new(path,trace)
                print(json.dumps({'config':trace['config']['id'],'query_id':trace['query_id'],
                                  'status':trace['status']},ensure_ascii=True),flush=True)
    if args.command=='select':
        if read(meta_path)['identity']!=current:
            raise ValueError('Code/config changed since dev')
        summaries = []
        for config in configs:
            dev = [c for c in cases if c['split']=='dev']
            traces = [read(args.output/'dev'/config['id']/(c['id']+'.json')) for c in dev]
            summaries.append({'config_id':config['id'],**summarize_retrieval(dev,traces)})
        write_new(args.output/'selection.dev.json',{'selected_at':datetime.now(timezone.utc).isoformat(),
            'selected_config':choose_config(summaries),'identity':current,
            'agent_model':read(meta_path)['agent_model'],'summaries':summaries,
            'rule':'context evidence count, first-tool Hit@3, fewer provider/retrieval errors, fewer tokens, config ID'})
    if args.command in ('run','summarize'):
        selected = [c for c in cases if c['split']==args.split]
        summaries = []
        for config in configs:
            directory = args.output/args.split/config['id']
            if not directory.exists(): continue
            traces = [read(directory/(c['id']+'.json')) for c in selected]
            summary = {'config_id':config['id'],**summarize_retrieval(selected,traces)}
            reviews_path = directory/'reviews.json'
            if reviews_path.exists():
                reviews = read(reviews_path)
                summary['agent_review'] = aggregate(selected,traces,reviews)
                summary['context_grades'] = {str(grade):sum(r.get('context_grade')==grade for r in reviews)
                                             for grade in (0,1,2)}
            summaries.append(summary)
        # Summary is derived, regenerable; raw per-case traces and selection are immutable.
        target = args.output/f'summary.{args.split}.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(summaries,ensure_ascii=True),flush=True)


if __name__=='__main__': main()
