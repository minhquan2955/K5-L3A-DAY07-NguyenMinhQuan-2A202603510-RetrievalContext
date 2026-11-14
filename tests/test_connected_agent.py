"""Behavioral checks; external APIs are replaced only at their network boundary."""
import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))
from baseline import TfidfIndex
from agentic import run_agent


def chunk(cid, text, chapter=1):
    return dict(id=cid, text=text, source_id='book', source='book.pdf', page=chapter,
                metadata={'chapter': chapter})


class ConnectedAgentTests(unittest.TestCase):
    def test_cli_records_configuration_errors_without_leaking_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env = root / 'settings.env'
            env.write_text('DATABASE_URL=not-a-dsn-with-secret-password\n', encoding='utf-8')
            output = root / 'trace.json'
            result = subprocess.run([sys.executable, '-X', 'utf8', 'starter/run.py', 'check',
                                     '--env-file', str(env), '--output', str(output)],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
                                    encoding='utf-8')
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(output.exists(), result.stderr)
            trace = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(trace['status'], 'error')
            self.assertNotIn('secret-password', output.read_text(encoding='utf-8') + result.stdout + result.stderr)

    def test_rrf_rewards_agreement_without_counting_duplicates(self):
        from retrieval import rrf
        a, b, c = chunk('a', 'alpha'), chunk('b', 'beta'), chunk('c', 'gamma')
        result = rrf([[a, b, b], [c, b]], top_k=3)
        self.assertEqual([r['id'] for r in result], ['b', 'a', 'c'])
        self.assertAlmostEqual(result[0]['score'], 2 / 62)
        self.assertEqual(result[0]['ranks'], {'dense': 2, 'tfidf': 2})

    def test_lexical_filter_precedes_top_k_and_rejects_unknown_filter(self):
        from retrieval import lexical_search
        index = TfidfIndex([chunk('a', 'alpha beta', 1), chunk('b', 'alpha', 2)])
        rows = lexical_search(index, 'alpha beta', {'chapter': 2}, 1)
        self.assertEqual([r['id'] for r in rows], ['b'])
        self.assertEqual(lexical_search(index, 'unseen', {}, 3), [])
        with self.assertRaises(ValueError):
            lexical_search(index, 'alpha', {'gold_page': 1}, 3)

    def test_filter_types_match_postgres_instead_of_python_bool_coercion(self):
        from retrieval import lexical_search
        index = TfidfIndex([chunk('a', 'alpha', 1)])
        self.assertEqual(lexical_search(index, 'alpha', {'chapter': True}, 3), [])
        self.assertEqual([r['id'] for r in lexical_search(index, 'alpha', {'chapter': 1.0}, 3)], ['a'])
        for filters in ({'page': '1'}, {'page': True}, {'source_id': 123}):
            with self.assertRaises(ValueError):
                lexical_search(index, 'alpha', filters, 3)

    def test_answer_cannot_hide_an_undeclared_citation(self):
        class Controller:
            def decide(self, question, history):
                if not history:
                    return {'action': 'search', 'query': 'alpha'}
                return {'action': 'answer', 'answer': 'Known [a], invented [outside].', 'citations': ['a']}
        class Retriever:
            def search(self, query, *, filters, top_k):
                return [chunk('a', 'alpha')]
        self.assertEqual(run_agent('q', Controller(), Retriever())['status'], 'abstain')

    def test_explicit_abstention_and_citation_boundary(self):
        class Controller:
            def decide(self, question, history):
                return {'action': 'abstain', 'answer': 'Không đủ bằng chứng.'}
        result = run_agent('q', Controller(), None)
        self.assertEqual(result['status'], 'abstain')
        self.assertEqual(result['events'][-1]['event'], 'abstain')

    def test_controller_normalizes_tool_calls_and_retains_usage(self):
        from model_controller import OpenAIController
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            function = SimpleNamespace(name='search', arguments='{"query":"alpha"}')
            return SimpleNamespace(model='test-model', usage=SimpleNamespace(
                prompt_tokens=10, completion_tokens=5, total_tokens=15),
                choices=[SimpleNamespace(message=SimpleNamespace(
                    tool_calls=[SimpleNamespace(function=function)]))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        controller = OpenAIController(client, 'test-model')
        self.assertEqual(controller.decide('q', []), {'action': 'search', 'query': 'alpha'})
        self.assertEqual(calls[0]['tool_choice']['function']['name'], 'search')
        self.assertEqual(controller.calls[0]['usage']['total_tokens'], 15)

    def test_controller_rejects_malformed_or_multiple_actions(self):
        from model_controller import parse_action
        with self.assertRaises(ValueError):
            parse_action('search', '{"query":""}')
        with self.assertRaises(ValueError):
            parse_action('answer', '{"answer":"x","citations":"invented"}')
        with self.assertRaises(ValueError):
            parse_action('delete_database', '{}')
        self.assertEqual(parse_action('abstain', '{"reason":"No evidence"}'),
                         {'action': 'abstain', 'answer': 'No evidence'})

    def test_luna_disables_reasoning_for_chat_function_tools(self):
        from model_controller import OpenAIController
        def create(**kwargs):
            self.assertEqual(kwargs.get('reasoning_effort'), 'none')
            return SimpleNamespace(model='gpt-6-luna', usage=SimpleNamespace(
                prompt_tokens=10, completion_tokens=5, total_tokens=15),
                choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[SimpleNamespace(
                    function=SimpleNamespace(name='search', arguments='{"query":"information systems"}'))]))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        result = OpenAIController(client, 'gpt-6-luna').decide('q', [])
        self.assertEqual(result['action'], 'search')

    def test_model_grouped_citations_are_formatted_without_inventing_sources(self):
        from model_controller import parse_action
        action = parse_action('answer', json.dumps({'answer': 'Supported [a, b].', 'citations': ['a', 'b']}))
        self.assertEqual(action['answer'], 'Supported [a][b].')
        unknown = parse_action('answer', json.dumps({'answer': 'Claim [a, invented].', 'citations': ['a']}))
        self.assertEqual(unknown['answer'], 'Claim [a, invented].')

    def test_structured_answer_sources_are_rendered_when_model_omits_inline_ids(self):
        from model_controller import parse_action
        action = parse_action('answer', '{"answer":"Supported claim.","citations":["a"]}')
        self.assertEqual(action['answer'], 'Supported claim. [a]')


if __name__ == '__main__':
    unittest.main()
