import threading
import copy
import logging

logger = logging.getLogger(__name__)

class InMemoryCollection:
    def __init__(self):
        self._docs = []
        self._id_counter = 1
        self._lock = threading.Lock()

    def create_index(self, *args, **kwargs):
        return

    def find_one(self, query):
        with self._lock:
            for doc in self._docs:
                if self._match(doc, query):
                    return copy.deepcopy(doc)
        return None

    def insert_one(self, doc):
        with self._lock:
            if '_id' not in doc:
                doc['_id'] = self._id_counter
                self._id_counter += 1
            self._docs.append(copy.deepcopy(doc))
        class Result:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        return Result(doc['_id'])

    def update_one(self, query, update):
        with self._lock:
            for idx, doc in enumerate(self._docs):
                if self._match(doc, query):
                    for op, changes in update.items():
                        if op == '$set':
                            for k, v in changes.items():
                                self._set_field(doc, k, v)
                        elif op == '$inc':
                            for k, v in changes.items():
                                current = self._get_field(doc, k) or 0
                                self._set_field(doc, k, current + v)
                        elif op == '$push':
                            for k, v in changes.items():
                                arr = self._get_field(doc, k)
                                if arr is None:
                                    self._set_field(doc, k, [v])
                                elif isinstance(arr, list):
                                    arr.append(v)
                                else:
                                    self._set_field(doc, k, [arr, v])
                    self._docs[idx] = copy.deepcopy(doc)
                    return

    def find(self, query=None):
        with self._lock:
            if query is None or query == {}:
                return copy.deepcopy(self._docs)
            return [copy.deepcopy(d) for d in self._docs if self._match(d, query)]

    def count_documents(self, query=None):
        with self._lock:
            if query is None or query == {}:
                return len(self._docs)
            return len([1 for d in self._docs if self._match(d, query)])

    def _match(self, doc, query):
        if not query:
            return True
        for k, v in query.items():
            doc_val = self._get_field(doc, k)
            if doc_val != v:
                return False
        return True

    def _get_field(self, doc, dotted_key):
        parts = str(dotted_key).split('.')
        val = doc
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return None
        return val

    def _set_field(self, doc, dotted_key, value):
        parts = str(dotted_key).split('.')
        cur = doc
        for i, p in enumerate(parts):
            if i == len(parts) - 1:
                cur[p] = value
            else:
                if p not in cur or not isinstance(cur[p], dict):
                    cur[p] = {}
                cur = cur[p]


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.users = InMemoryCollection()
        self.tickets = InMemoryCollection()
        self.transactions = InMemoryCollection()
        self.raffles = InMemoryCollection()
        logger.info("In-memory DB initialized")

db = Database()
