import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/raffle_system')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
FLASK_SECRET = os.getenv('FLASK_SECRET', 'your-secret-key')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://your_domain.com')

# Raffle Constants
TICKET_PRICE = 0.5  # TON
MAX_TICKETS_TOTAL = 1000
MAX_TICKETS_PER_USER = 20
MIN_TICKETS_FOR_DRAW = 700
PRIZE_POOL = 100  # TON
NUMBERS_PER_TICKET = 6
MAX_NUMBER = 50
REFERRAL_COMMISSION = 0.10  # 10%

# Database
DATABASE_NAME = 'raffle_system'