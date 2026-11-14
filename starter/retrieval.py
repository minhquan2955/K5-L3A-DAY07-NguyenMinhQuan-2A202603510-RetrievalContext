"""Read-only retrieval over one existing Day06 pgvector snapshot."""
import math
import time

from baseline import TfidfIndex

FILTER_KEYS = {'document_id', 'source_id', 'source', 'page', 'chapter', 'section',
               'year', 'language', 'category', 'version', 'audience',
               'effective_date', 'document_type'}


def validate_search(query, filters, top_k):
    if not isinstance(query, str) or not query.strip():
        raise ValueError('query must be nonempty text')
    if type(top_k) is not int or top_k < 1:
        raise ValueError('top_k must be a positive integer')
    if not isinstance(filters, dict) or set(filters) - FILTER_KEYS:
        raise ValueError('Unsupported metadata filter')
    if 'page' in filters and (type(filters['page']) is not int or filters['page'] < 1):
        raise ValueError('page filter must be a positive integer')
    for key in ('document_id', 'source_id', 'source'):
        if key in filters and (not isinstance(filters[key], str) or not filters[key].strip()):
            raise ValueError('Document and source filters must be nonempty text')
    for value in filters.values():
        if not isinstance(value, (str, int, float, bool)) or (
                isinstance(value, float) and not math.isfinite(value)):
            raise ValueError('Filter values must be finite scalar values')


def lexical_search(index, query, filters, top_k):
    validate_search(query, filters, top_k)
    # Rank the same corpus, then filter BEFORE the requested cutoff.
    rows = index.search(query, top_k=len(index.chunks))
    def matches(row):
        fields = {**row['metadata'], 'document_id': row['source_id'],
                  'source_id': row['source_id'], 'source': row['source'], 'page': row['page']}
        # JSONB distinguishes true from 1; Python equality alone does not.
        return all(isinstance(fields.get(key), bool) == isinstance(value, bool)
                   and fields.get(key) == value for key, value in filters.items())
    return [row for row in rows if matches(row)][:top_k]


def rrf(rankings, top_k, constant=60):
    """Fuse dense and lexical rankings, independent of their score scales."""
    if type(top_k) is not int or top_k < 1 or constant <= 0:
        raise ValueError('Invalid RRF cutoff or constant')
    fused = {}
    for name, rows in zip(('dense', 'tfidf'), rankings):
        seen = set()
        for rank, row in enumerate(rows, 1):
            if row['id'] in seen:
                continue
            seen.add(row['id'])
            item = fused.setdefault(row['id'], {**row, 'score': 0.0, 'strategy': 'hybrid', 'ranks': {}})
            item['score'] += 1 / (constant + rank)
            item['ranks'][name] = rank
    return sorted(fused.values(), key=lambda row: (-row['score'], row['id']))[:top_k]


class Day6Retriever:
    def __init__(self, database_url, *, method='dense', strategy='B',
                 embedding_model='text-embedding-3-small', dimensions=1536,
                 candidate_k=20, client=None):
        import psycopg
        from psycopg.rows import dict_row
        if method not in {'dense', 'tfidf', 'hybrid'}:
            raise ValueError('Unknown retrieval method')
        if type(dimensions) is not int or dimensions < 1 or type(candidate_k) is not int or candidate_k < 1:
            raise ValueError('dimensions and candidate_k must be positive integers')
        self.database_url, self.method, self.strategy = database_url, method, strategy
        self.embedding_model, self.dimensions = embedding_model, dimensions
        self.candidate_k, self.client = candidate_k, client
        self.calls, self.embedding_usage = [], []
        with psycopg.connect(database_url, connect_timeout=5, row_factory=dict_row) as connection:
            connection.execute('SET TRANSACTION READ ONLY')
            rows = connection.execute('''SELECT chunk_id AS id, document_id AS source_id,
                source, page, text, metadata, vector_dims(embedding) AS dimensions
                FROM public.day6_chunks WHERE strategy = %s ORDER BY chunk_id''', (strategy,)).fetchall()
        if not rows:
            raise ValueError('Selected Day06 strategy contains no chunks')
        if any(row.pop('dimensions') != dimensions for row in rows):
            raise ValueError('Query embedding dimensions differ from the Day06 index')
        fingerprints = {row['metadata'].get('run_fingerprint') for row in rows}
        if len(fingerprints) != 1:
            raise ValueError('Mixed Day06 snapshots; select a consistent index')
        self.fingerprint = fingerprints.pop()
        self.chunks = rows
        self.index = TfidfIndex(rows)

    def _dense(self, query, filters, top_k):
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
        if self.client is None:
            from openai import OpenAI
            self.client = OpenAI(timeout=45, max_retries=1)
        response = self.client.embeddings.create(model=self.embedding_model, input=[query],
                                                 dimensions=self.dimensions, encoding_format='float')
        vector = response.data[0].embedding
        if len(vector) != self.dimensions or any(not math.isfinite(v) for v in vector) or not any(vector):
            raise ValueError('Embedding provider returned an invalid vector')
        self.embedding_usage.append({'model': response.model,
                                     'total_tokens': response.usage.total_tokens})
        vector = '[' + ','.join(str(float(value)) for value in vector) + ']'
        clauses = [sql.SQL('strategy = %s'),
                   sql.SQL("metadata->>'run_fingerprint' IS NOT DISTINCT FROM %s")]
        params = [vector, self.strategy, self.fingerprint]
        for key, value in filters.items():
            column = 'document_id' if key in {'document_id', 'source_id'} else key
            if column in {'document_id', 'source', 'page'}:
                clauses.append(sql.SQL('{} = %s').format(sql.Identifier(column)))
                params.append(value)
            else:
                clauses.append(sql.SQL('metadata @> %s'))
                params.append(Jsonb({key: value}))
        statement = sql.SQL('''SELECT chunk_id AS id, document_id AS source_id,
            source, page, text, metadata, 1 - (embedding <=> %s::vector) AS score
            FROM public.day6_chunks WHERE {} ORDER BY embedding <=> %s::vector, chunk_id LIMIT %s''').format(
                sql.SQL(' AND ').join(clauses))
        with psycopg.connect(self.database_url, connect_timeout=5, row_factory=dict_row) as connection:
            connection.execute('SET TRANSACTION READ ONLY')
            rows = connection.execute(statement, [*params, vector, top_k]).fetchall()
        return [{**row, 'strategy': 'dense'} for row in rows]

    def search(self, query, *, filters=None, top_k=3):
        filters = {} if filters is None else filters
        validate_search(query, filters, top_k)
        started = time.perf_counter()
        call = {'query': query, 'filter': filters, 'method': self.method, 'top_k': top_k}
        self.calls.append(call)
        try:
            if self.method == 'tfidf':
                rows = lexical_search(self.index, query, filters, top_k)
            elif self.method == 'dense':
                rows = self._dense(query, filters, top_k)
            else:
                cutoff = max(top_k, self.candidate_k)
                dense = self._dense(query, filters, cutoff)
                lexical = lexical_search(self.index, query, filters, cutoff)
                call['rankings'] = {'dense': dense, 'tfidf': lexical}
                rows = rrf([dense, lexical], top_k)
            rows = [{**row, 'rank': rank} for rank, row in enumerate(rows, 1)]
            call['results'] = rows
            return rows
        except Exception as exc:
            call['error_type'] = type(exc).__name__
            raise
        finally:
            call['elapsed_ms'] = (time.perf_counter() - started) * 1000
