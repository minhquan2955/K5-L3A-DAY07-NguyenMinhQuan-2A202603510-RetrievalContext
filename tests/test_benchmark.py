import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))


class BenchmarkTests(unittest.TestCase):
    def test_metrics_use_final_context_and_exclude_unanswerable(self):
        from benchmark import summarize_retrieval
        chunk = {'id':'a','source_id':'book','page':2,'text':'A valid definition.'}
        cases = [{'id':'q1','answerable':True,'gold':[{'source_id':'book','page':2,'evidence':'valid definition'}]},
                 {'id':'q2','answerable':False}]
        traces = [{'query_id':'q1','status':'answered','original_retrieval':{'status':'ok','results':[chunk]},
                   'events':[{'event':'search','results':[],'context_ids':[]},
                             {'event':'search','results':[chunk],'context_ids':['a']}],
                   'model_calls':[],'embedding_usage':[],'elapsed_ms':1},
                  {'query_id':'q2','status':'abstain','original_retrieval':{'status':'ok','results':[]},
                   'events':[],'model_calls':[],'embedding_usage':[],'elapsed_ms':1}]
        summary = summarize_retrieval(cases,traces)
        self.assertEqual(summary['original_hit1'], {'n':1,'N':1})
        self.assertEqual(summary['first_tool_hit3'], {'n':0,'N':1})
        self.assertEqual(summary['context_evidence'], {'n':1,'N':1})

    def test_selection_is_deterministic_and_prefers_evidence_before_tokens(self):
        from benchmark import choose_config
        summaries = [
            {'config_id':'cheap','context_evidence':{'n':1,'N':2},'first_tool_hit3':{'n':2,'N':2},'provider_errors':0,'total_tokens':1},
            {'config_id':'better','context_evidence':{'n':2,'N':2},'first_tool_hit3':{'n':1,'N':2},'provider_errors':0,'total_tokens':100}]
        self.assertEqual(choose_config(summaries), 'better')

    def test_only_question_and_explicit_filter_cross_agent_boundary(self):
        from benchmark import agent_input
        case={'question':'Vietnamese query','filter':{'chapter':1},'gold':['SECRET'],'expected_answer':'SECRET'}
        self.assertEqual(agent_input(case), ('Vietnamese query',{'chapter':1}))

    def test_identity_binds_corpus_reference_and_accepts_relative_paths(self):
        from benchmark import identity
        result=identity(Path('benchmark/configs.json'),Path('benchmark/configs.json'))
        self.assertIn('data/day06_reference.json',result)

    def test_partial_search_events_survive_a_later_model_failure(self):
        from agentic import run_agent
        class Controller:
            def decide(self,q,history):
                if history: raise ConnectionError('provider unavailable')
                return {'action':'search','query':'q'}
        class Retriever:
            def search(self,q,**kwargs):
                return [{'id':'a','text':'evidence','source_id':'book','source':'book.pdf','page':1,'metadata':{}}]
        events=[]
        with self.assertRaises(ConnectionError):
            run_agent('q',Controller(),Retriever(),events=events)
        self.assertEqual(events[0]['event'],'search')
        self.assertEqual(events[0]['context_ids'],['a'])


if __name__=='__main__': unittest.main()
