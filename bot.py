import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, ADMIN_ID
from models import User, Ticket, Raffle, Transaction
from database import db
import random
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get bot token from . env
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN: 
    logger.error("❌ TELEGRAM_BOT_TOKEN not found in .env file!")
    raise ValueError("TELEGRAM_BOT_TOKEN is required")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Define states for conversation
class BuyTicketStates(StatesGroup):
    selecting_amount = State()
    confirming_wallet = State()
    waiting_for_txid = State()

# Main menu keyboard
def get_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎟️ My Tickets', callback_data='my_tickets')],
        [InlineKeyboardButton(text='💳 Buy Ticket', callback_data='buy_ticket')],
        [InlineKeyboardButton(text='📊 Tickets Left', callback_data='tickets_left')],
        [InlineKeyboardButton(text='ℹ️ Information', callback_data='info')]
    ])
    return keyboard

# Amount selection keyboard (1-20)
def get_amount_keyboard():
    buttons = []
    for i in range(1, 21):
        buttons.append(InlineKeyboardButton(text=str(i), callback_data=f'amount_{i}'))
    
    # Create a grid layout (5 columns)
    keyboard_buttons = [buttons[i: i+5] for i in range(0, len(buttons), 5)]
    keyboard_buttons.append([InlineKeyboardButton(text='❌ Cancel', callback_data='cancel_buy')])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

@dp.message(Command('start'))
async def start_command(message: types.Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or 'User'
    first_name = message.from_user.first_name or 'User'
    
    logger.info(f"✅ User {user_id} ({first_name}) started the bot")
    
    # Create user if doesn't exist
    try:
        User.get_or_create(user_id, username, first_name)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
    
    await state.clear()
    
    await message.answer(
        '🎰 *Welcome to TON Raffle System!*\n\n'
        '💰 Prize Pool: 100 TON\n'
        '🎟️ Max Tickets: 1000 (Limited)\n'
        '💵 Price:  0.5 TON per ticket\n'
        '👤 Max per person: 20 tickets\n'
        '✅ Draws when 700+ tickets sold\n\n'
        'Select an option below: ',
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )

@dp.callback_query(F.data == 'my_tickets')
async def my_tickets(callback: types.CallbackQuery):
    """Show user tickets"""
    user_id = callback.from_user.id
    
    try:
        user = User.get_user(user_id)
        
        if not user:
            await callback.answer('❌ User not found', show_alert=True)
            return
        
        tickets = Ticket.get_user_tickets(user_id)
        user_tickets_count = Ticket.count_user_tickets(user_id)
        
        if user_tickets_count == 0:
            message_text = '🎟️ *Your Tickets*\n\nYou don\'t have any tickets yet.\nStart by clicking "💳 Buy Ticket"!'
        else:
            message_text = f'🎟️ *Your Tickets* ({user_tickets_count} total)\n\n'
            for idx, ticket in enumerate(tickets, 1):
                numbers = ', '.join(map(str, ticket['numbers']))
                message_text += f'*Ticket #{idx}*:  {numbers}\n'
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Back', callback_data='back_to_menu')]
        ])
        
        await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e: 
        logger.error(f"Error in my_tickets:  {e}")
        await callback. answer(f'❌ Error: {str(e)}', show_alert=True)
    
    await callback.answer()

@dp.callback_query(F.data == 'buy_ticket')
async def buy_ticket_start(callback: types.CallbackQuery, state: FSMContext):
    """Start ticket buying process"""
    user_id = callback.from_user.id
    
    try:
        user = User.get_user(user_id)
        
        if not user:
            await callback. answer('❌ User not found', show_alert=True)
            return
        
        user_tickets = Ticket.count_user_tickets(user_id)
        can_buy = 20 - user_tickets
        
        if can_buy <= 0:
            await callback.message.edit_text(
                '❌ *Cannot Buy More Tickets*\n\n'
                'You have reached the maximum of 20 tickets per person.',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Back', callback_data='back_to_menu')]]),
                parse_mode='Markdown'
            )
            await callback.answer()
            return
        
        raffle_stats = Raffle.get_raffle_stats()
        if raffle_stats['tickets_sold'] >= raffle_stats['max_tickets']:
            await callback.message.edit_text(
                '❌ *All Tickets Sold Out*\n\n'
                'No more tickets available for this raffle.',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Back', callback_data='back_to_menu')]]),
                parse_mode='Markdown'
            )
            await callback.answer()
            return
        
        await state.set_state(BuyTicketStates.selecting_amount)
        
        await callback.message.edit_text(
            f'💳 *How many tickets do you want to buy?*\n\n'
            f'You can buy up to {can_buy} more tickets\n'
            f'💵 Price: 0.5 TON per ticket',
            reply_markup=get_amount_keyboard(),
            parse_mode='Markdown'
        )
    except Exception as e: 
        logger.error(f"Error in buy_ticket_start:  {e}")
        await callback. answer(f'❌ Error: {str(e)}', show_alert=True)
    
    await callback.answer()

@dp.callback_query(BuyTicketStates.selecting_amount, F.data. startswith('amount_'))
async def select_amount(callback: types.CallbackQuery, state: FSMContext):
    """Handle ticket amount selection"""
    user_id = callback.from_user.id
    
    try:
        user = User.get_user(user_id)
        amount = int(callback.data.split('_')[1])
        
        user_tickets = Ticket.count_user_tickets(user_id)
        can_buy = 20 - user_tickets
        
        if amount > can_buy:
            await callback.answer('❌ You can\'t buy that many tickets! ', show_alert=True)
            return
        
        raffle_stats = Raffle. get_raffle_stats()
        if raffle_stats['tickets_sold'] + amount > raffle_stats['max_tickets']:
            remaining = raffle_stats['max_tickets'] - raffle_stats['tickets_sold']
            await callback.answer(f'❌ Only {remaining} tickets left!', show_alert=True)
            return
        
        # Store amount in state
        await state.update_data(amount=amount)
        
        # Calculate total cost
        total_cost = amount * 0.5
        
        # Get wallet address
        wallet = user.get('wallet_address', '⚠️ Not set yet')
        
        await state.set_state(BuyTicketStates.confirming_wallet)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✅ Proceed to Payment', callback_data='confirm_payment')],
            [InlineKeyboardButton(text='❌ Cancel', callback_data='cancel_buy')]
        ])
        
        await callback.message.edit_text(
            f'💳 *Payment Details*\n\n'
            f'🎟️ Tickets:  {amount}\n'
            f'💵 Price per ticket: 0.5 TON\n'
            f'💰 *Total:  {total_cost} TON*\n\n'
            f'📍 *Your Wallet Address: *\n'
            f'`{wallet}`\n\n'
            f'After payment, you\'ll need to provide the transaction ID.',
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in select_amount: {e}")
        await callback.answer(f'❌ Error: {str(e)}', show_alert=True)
    
    await callback.answer()

@dp.callback_query(BuyTicketStates.confirming_wallet, F.data == 'confirm_payment')
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext):
    """Ask for transaction ID"""
    await state.set_state(BuyTicketStates.waiting_for_txid)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='❌ Cancel', callback_data='cancel_buy')]
    ])
    
    await callback.message. edit_text(
        '📝 *Enter Transaction ID*\n\n'
        'Please send the transaction ID (TXID) from your TON wallet to confirm the purchase.\n\n'
        '_Example: EQDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx_',
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    await callback.answer()

@dp.message(BuyTicketStates.waiting_for_txid)
async def receive_txid(message: types. Message, state: FSMContext):
    """Process transaction ID and create tickets"""
    user_id = message.from_user.id
    txid = message.text.strip()
    
    try:
        # Validate TXID format (basic check)
        if len(txid) < 10: 
            await message.answer('❌ Invalid Transaction ID.  Please try again.')
            return
        
        data = await state.get_data()
        amount = data.get('amount', 1)
        
        # Create tickets
        raffle = Raffle. get_active_raffle()
        tickets_created = []
        
        for _ in range(amount):
            ticket = Ticket. create_ticket(user_id, raffle['_id'])
            Raffle.add_ticket(user_id)
            tickets_created.append(ticket)
        
        # Update user
        user = User.get_user(user_id)
        total_cost = amount * 0.5
        User.update_user(user_id, {
            'total_spent': user.get('total_spent', 0) + total_cost,
            'tickets_owned':  Ticket.count_user_tickets(user_id)
        })
        
        # Create transaction record
        Transaction.create_transaction(user_id, 'purchase', total_cost, amount, txid=txid)
        
        # Show confirmation
        message_text = f'✅ *Purchase Confirmed!*\n\n🎟️ You bought {amount} ticket(s)\n\n'
        
        for idx, ticket in enumerate(tickets_created, 1):
            numbers = ', '.join(map(str, ticket['numbers']))
            message_text += f'*Ticket #{idx}*:  {numbers}\n'
        
        message_text += (
            f'\n💰 Total:  {total_cost} TON\n\n'
            f'📢 Go to the channel and wait for the raffle results!\n'
            f'Good luck!  🍀'
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🎰 Back to Menu', callback_data='back_to_menu')]
        ])
        
        await message.answer(message_text, reply_markup=keyboard, parse_mode='Markdown')
        await state.clear()
        
        logger.info(f"✅ User {user_id} purchased {amount} tickets for {total_cost} TON")
        
    except Exception as e:
        logger.error(f'Error processing tickets: {e}')
        await message.answer(f'❌ Error processing your purchase: {str(e)}\n\nPlease try again.')

@dp.callback_query(F.data == 'tickets_left')
async def tickets_left(callback: types.CallbackQuery):
    """Show remaining tickets"""
    try:
        raffle_stats = Raffle.get_raffle_stats()
        
        percentage = (raffle_stats['tickets_sold'] / raffle_stats['max_tickets']) * 100
        status = '🟢 Ready to Draw!' if raffle_stats['is_ready_for_draw'] else '⏳ In Progress'
        
        message_text = (
            f'📊 *Raffle Status*\n\n'
            f'🎟️ Sold: {raffle_stats["tickets_sold"]}/{raffle_stats["max_tickets"]}\n'
            f'📈 Progress: {percentage:.1f}%\n'
            f'⏳ Needed: {max(0, raffle_stats["need_for_draw"])} more to draw\n\n'
            f'Status: {status}'
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Back', callback_data='back_to_menu')]
        ])
        
        await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e: 
        logger.error(f"Error in tickets_left: {e}")
        await callback.answer(f'❌ Error: {str(e)}', show_alert=True)
    
    await callback.answer()

@dp.callback_query(F.data == 'info')
async def raffle_info(callback: types. CallbackQuery):
    """Show raffle information"""
    try: 
        raffle_stats = Raffle.get_raffle_stats()
        
        message_text = (
            f'ℹ️ *Raffle Information*\n\n'
            f'💰 Prize Pool: 100 TON\n'
            f'🎟️ Total Tickets: {raffle_stats["max_tickets"]}\n'
            f'💵 Ticket Price: 0.5 TON\n'
            f'👤 Max per Person: 20 tickets\n'
            f'🎯 Numbers per Ticket: 6 (from 1-50)\n\n'
            f'*How it Works: *\n'
            f'1️⃣ Buy tickets for 0.5 TON each\n'
            f'2️⃣ Each ticket has 6 random numbers (1-50)\n'
            f'3️⃣ When 700+ tickets sold, draw happens\n'
            f'4️⃣ Winners share the 100 TON prize!\n\n'
            f'📢 Join our channel for draw results!'
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Back', callback_data='back_to_menu')]
        ])
        
        await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e: 
        logger.error(f"Error in raffle_info: {e}")
        await callback.answer(f'❌ Error: {str(e)}', show_alert=True)
    
    await callback. answer()

@dp.callback_query(F.data == 'back_to_menu')
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Back to main menu"""
    await state.clear()
    
    user_id = callback.from_user.id
    
    try:
        user = User.get_user(user_id)
        user_tickets = Ticket.count_user_tickets(user_id)
        
        message_text = (
            f'🎰 *TON Raffle System*\n\n'
            f'👤 Your Tickets: {user_tickets}\n'
            f'💰 Total Spent: {user.get("total_spent", 0):. 2f} TON\n\n'
            f'Select an option:'
        )
        
        await callback.message.edit_text(message_text, reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in back_to_menu: {e}")
        await callback.answer(f'❌ Error: {str(e)}', show_alert=True)
    
    await callback.answer()

@dp.callback_query(F. data == 'cancel_buy')
async def cancel_buy(callback: types.CallbackQuery, state: FSMContext):
    """Cancel ticket purchase"""
    await state.clear()
    await back_to_menu(callback, state)

@dp.message(Command('draw'))
async def draw_command(message: types.Message):
    """Admin command to draw winners"""
    if message.from_user.id != ADMIN_ID:
        await message.answer('❌ Unauthorized')
        return
    
    try:
        raffle_stats = Raffle.get_raffle_stats()
        
        if not raffle_stats['is_ready_for_draw']:
            await message.answer(f'❌ Not enough tickets.  Need {raffle_stats["need_for_draw"]} more.')
            return
        
        await message.answer('🎰 Drawing raffle winners.. .')
        
        raffle = Raffle.get_active_raffle()
        all_tickets = list(db.tickets.find({'raffle_id': raffle['_id']}))
        
        winning_numbers = Ticket.generate_numbers()
        
        await message.answer(f'🎯 *Winning Numbers: * {", ".join(map(str, winning_numbers))}', parse_mode='Markdown')
        
        winners = []
        for ticket in all_tickets:
            matches = len([n for n in ticket['numbers'] if n in winning_numbers])
            if matches >= 4:
                winners.append(ticket['user_id'])
        
        if not winners:
            await message. answer('❌ No winners!  Prize rolls over to next raffle.')
            Raffle.finish_raffle([])
            return
        
        from config import PRIZE_POOL
        prize_per_winner = PRIZE_POOL / len(winners)
        
        for winner_id in winners:
            User.add_balance(winner_id, prize_per_winner)
            try:
                await bot.send_message(
                    winner_id,
                    f'🎉 *Congratulations!*\n\n'
                    f'You won {prize_per_winner:. 2f} TON!\n\n'
                    f'🎯 Winning numbers: {", ".join(map(str, winning_numbers))}',
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f'Could not notify user {winner_id}: {e}')
        
        Raffle.finish_raffle(winners)
        
        await message.answer(f'✅ Draw complete! {len(winners)} winner(s) found.')
        logger.info(f"✅ Raffle draw completed with {len(winners)} winners")
        
    except Exception as e: 
        logger.error(f"Error in draw_command: {e}")
        await message.answer(f'❌ Error during draw: {str(e)}')

async def main():
    logger.info('🤖 Bot is starting...')
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
