from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import MONGODB_URI, DATABASE_NAME
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        try:
            self.client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self._db = self.client[DATABASE_NAME]
            
            # Create collections
            self.users = self._db['users']
            self.tickets = self._db['tickets']
            self.transactions = self._db['transactions']
            self.raffles = self._db['raffles']
            
            # Create indexes
            self.users.create_index('user_id')
            self.tickets.create_index('user_id')
            self.tickets.create_index('raffle_id')
            self.transactions.create_index('user_id')
            self.transactions.create_index('timestamp')
            
            logger.info('✅ Connected to MongoDB')
        except ConnectionFailure as e:
            logger.error(f'❌ MongoDB connection error: {e}')
            raise

    def get_db(self):
        if self._db is None:
            self._initialize()
        return self._db

# Initialize database
db = Database()