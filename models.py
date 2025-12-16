from datetime import datetime
from config import MAX_TICKETS_PER_USER, REFERRAL_COMMISSION
import random
import string

class User:
    @staticmethod
    def get_or_create(user_id, username, first_name):
        """Get or create a user"""
        from database import db
        user = db.users.find_one({'user_id': user_id})
        
        if not user:
            user = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'balance': 0.0,
                'total_spent': 0.0,
                'tickets_owned': 0,
                'referral_code': User.generate_referral_code(),
                'referrals': [],
                'referral_earnings': 0.0,
                'joined_at': datetime.now(),
                'wallet_address': None,
                'referred_by': None
            }
            db.users.insert_one(user)
        
        return user

    @staticmethod
    def generate_referral_code():
        """Generate unique referral code"""
        return 'REF' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    @staticmethod
    def get_user(user_id):
        """Get user by ID"""
        from database import db
        return db.users.find_one({'user_id': user_id})

    @staticmethod
    def update_user(user_id, update_dict):
        """Update user information"""
        from database import db
        return db.users.update_one({'user_id': user_id}, {'$set': update_dict})

    @staticmethod
    def set_wallet(user_id, wallet_address):
        """Set user wallet address"""
        from database import db
        return db.users.update_one(
            {'user_id': user_id},
            {'$set': {'wallet_address': wallet_address}}
        )

    @staticmethod
    def add_balance(user_id, amount):
        """Add balance to user"""
        from database import db
        return db.users.update_one(
            {'user_id': user_id},
            {'$inc': {'balance': amount}}
        )

    @staticmethod
    def apply_referral(referrer_id, amount):
        """Apply referral commission"""
        commission = amount * REFERRAL_COMMISSION
        from database import db
        return db.users.update_one(
            {'user_id': referrer_id},
            {'$inc': {'referral_earnings': commission}}
        )


class Ticket:
    @staticmethod
    def generate_numbers():
        """Generate 6 random numbers from 1-50"""
        from config import NUMBERS_PER_TICKET, MAX_NUMBER
        numbers = set()
        while len(numbers) < NUMBERS_PER_TICKET:
            numbers.add(random.randint(1, MAX_NUMBER))
        return sorted(list(numbers))

    @staticmethod
    def create_ticket(user_id, raffle_id):
        """Create a ticket"""
        from database import db
        ticket = {
            'user_id': user_id,
            'raffle_id': raffle_id,
            'numbers': Ticket.generate_numbers(),
            'purchased_at': datetime.now()
        }
        result = db.tickets.insert_one(ticket)
        return ticket

    @staticmethod
    def get_user_tickets(user_id, raffle_id=None):
        """Get user's tickets"""
        from database import db
        query = {'user_id': user_id}
        if raffle_id:
            query['raffle_id'] = raffle_id
        return list(db.tickets.find(query))

    @staticmethod
    def count_user_tickets(user_id, raffle_id=None):
        """Count user's tickets"""
        from database import db
        query = {'user_id': user_id}
        if raffle_id:
            query['raffle_id'] = raffle_id
        return db.tickets.count_documents(query)


class Raffle:
    @staticmethod
    def get_active_raffle():
        """Get active raffle"""
        from database import db
        raffle = db.raffles.find_one({'active': True})
        
        if not raffle:
            raffle = {
                'active': True,
                'tickets_sold': 0,
                'user_tickets': {},
                'started_at': datetime.now(),
                'winners': [],
                'prize_per_winner': 0
            }
            db.raffles.insert_one(raffle)
        
        return raffle

    @staticmethod
    def get_raffle_stats():
        """Get raffle statistics"""
        from config import MAX_TICKETS_TOTAL, MIN_TICKETS_FOR_DRAW
        from database import db
        
        raffle = Raffle.get_active_raffle()
        tickets_sold = raffle['tickets_sold']
        
        return {
            'tickets_sold': tickets_sold,
            'max_tickets': MAX_TICKETS_TOTAL,
            'remaining': MAX_TICKETS_TOTAL - tickets_sold,
            'is_ready_for_draw': tickets_sold >= MIN_TICKETS_FOR_DRAW,
            'need_for_draw': max(0, MIN_TICKETS_FOR_DRAW - tickets_sold)
        }

    @staticmethod
    def add_ticket(user_id):
        """Add ticket count to raffle"""
        from database import db
        raffle = Raffle.get_active_raffle()
        user_tickets = raffle['user_tickets'].get(str(user_id), 0)
        
        db.raffles.update_one(
            {'_id': raffle['_id']},
            {
                '$inc': {'tickets_sold': 1},
                '$set': {f'user_tickets.{user_id}': user_tickets + 1}
            }
        )

    @staticmethod
    def finish_raffle(winners):
        """Mark raffle as finished and start new one"""
        from database import db
        db.raffles.update_one({'active': True}, {'$set': {'active': False}})
        
        new_raffle = {
            'active': True,
            'tickets_sold': 0,
            'user_tickets': {},
            'started_at': datetime.now(),
            'winners': winners,
            'prize_per_winner': 0
        }
        db.raffles.insert_one(new_raffle)


class Transaction:
    @staticmethod
    def create_transaction(user_id, tx_type, amount, ticket_count=None, status='completed'):
        """Create a transaction record"""
        from database import db
        transaction = {
            'user_id': user_id,
            'type': tx_type,
            'amount': amount,
            'ticket_count': ticket_count,
            'status': status,
            'timestamp': datetime.now()
        }
        db.transactions.insert_one(transaction)
        return transaction

    @staticmethod
    def get_user_transactions(user_id, limit=10):
        """Get user's transactions"""
        from database import db
        return list(db.transactions.find({'user_id': user_id}).sort('timestamp', -1).limit(limit))