from flask import Flask, render_template, request, jsonify, session
from config import FLASK_SECRET, FLASK_PORT, MAX_TICKETS_TOTAL, TICKET_PRICE, MAX_TICKETS_PER_USER
from models import User, Ticket, Raffle, Transaction
from database import db
from functools import wraps
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = FLASK_SECRET

# Middleware to get user from Telegram
def require_telegram_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In production, verify Telegram WebApp data
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401
        
        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({'error': 'Invalid user'}), 401
        
        return f(user_id, *args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Serve web app"""
    return render_template('index.html')

@app.route('/api/user', methods=['GET'])
@require_telegram_user
def get_user(user_id):
    """Get user information"""
    user = User.get_user(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user_tickets = Ticket.count_user_tickets(user_id)
    raffle_stats = Raffle.get_raffle_stats()
    
    return jsonify({
        'user_id': user['user_id'],
        'username': user.get('username'),
        'balance': user.get('balance', 0),
        'total_spent': user.get('total_spent', 0),
        'tickets_owned': user_tickets,
        'wallet_address': user.get('wallet_address'),
        'referral_code': user.get('referral_code'),
        'referrals_count': len(user.get('referrals', [])),
        'referral_earnings': user.get('referral_earnings', 0),
        'raffle_stats': raffle_stats
    })

@app.route('/api/raffle/stats', methods=['GET'])
def get_raffle_stats():
    """Get raffle statistics"""
    stats = Raffle.get_raffle_stats()
    return jsonify(stats)

@app.route('/api/tickets', methods=['GET'])
@require_telegram_user
def get_tickets(user_id):
    """Get user tickets"""
    tickets = Ticket.get_user_tickets(user_id)
    
    return jsonify({
        'tickets': [
            {
                'id': str(ticket['_id']),
                'numbers': ticket['numbers'],
                'purchased_at': ticket['purchased_at'].isoformat()
            }
            for ticket in tickets
        ]
    })

@app.route('/api/buy-tickets', methods=['POST'])
@require_telegram_user
def buy_tickets(user_id):
    """Buy tickets"""
    data = request.json
    amount = data.get('amount', 1)
    
    # Validation
    if amount < 1 or amount > MAX_TICKETS_PER_USER:
        return jsonify({'error': 'Invalid amount'}), 400
    
    user = User.get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if not user.get('wallet_address'):
        return jsonify({'error': 'Wallet not connected'}), 400
    
    user_tickets = Ticket.count_user_tickets(user_id)
    can_buy = MAX_TICKETS_PER_USER - user_tickets
    
    if amount > can_buy:
        return jsonify({'error': f'Can only buy {can_buy} more tickets'}), 400
    
    raffle_stats = Raffle.get_raffle_stats()
    if raffle_stats['tickets_sold'] + amount > MAX_TICKETS_TOTAL:
        return jsonify({'error': 'Not enough tickets available'}), 400
    
    # Create tickets
    raffle = Raffle.get_active_raffle()
    tickets_created = []
    
    for _ in range(amount):
        ticket = Ticket.create_ticket(user_id, raffle['_id'])
        Raffle.add_ticket(user_id)
        tickets_created.append(ticket)
    
    # Update user
    total_cost = amount * TICKET_PRICE
    User.update_user(user_id, {
        'total_spent': user['total_spent'] + total_cost,
        'tickets_owned': user_tickets + amount
    })
    
    # Create transaction
    Transaction.create_transaction(user_id, 'purchase', total_cost, amount)
    
    # Apply referral
    if user.get('referred_by'):
        if raffle_stats['tickets_sold'] + amount >= 700:
            User.apply_referral(user['referred_by'], total_cost)
    
    return jsonify({
        'success': True,
        'tickets': [
            {
                'numbers': t['numbers'],
                'id': str(t['_id'])
            }
            for t in tickets_created
        ],
        'total_cost': total_cost,
        'new_stats': Raffle.get_raffle_stats()
    })

@app.route('/api/wallet', methods=['POST'])
@require_telegram_user
def set_wallet(user_id):
    """Set wallet address"""
    data = request.json
    wallet = data.get('wallet', '').strip()
    
    # Validate TON address
    if not wallet.startswith('EQ') or len(wallet) != 66:
        return jsonify({'error': 'Invalid wallet address'}), 400
    
    User.set_wallet(user_id, wallet)
    
    return jsonify({
        'success': True,
        'wallet': wallet
    })

@app.route('/api/transactions', methods=['GET'])
@require_telegram_user
def get_transactions(user_id):
    """Get user transactions"""
    transactions = Transaction.get_user_transactions(user_id)
    
    return jsonify({
        'transactions': [
            {
                'type': t['type'],
                'amount': t['amount'],
                'status': t['status'],
                'timestamp': t['timestamp'].isoformat()
            }
            for t in transactions
        ]
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f'Server error: {error}')
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)