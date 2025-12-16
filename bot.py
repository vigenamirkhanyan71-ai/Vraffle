import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo # Import WebAppInfo
from config import BOT_TOKEN, ADMIN_ID
from models import User
from database import db

# --- CONFIGURATION ---
# PASTE YOUR NEW VERCEL LINK HERE (NOT THE GITHUB LINK)
# It should look like: https://vraffle.vercel.app
WEB_APP_URL = 'https://vraffle.vercel.app' 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command('start'))
async def start_command(message: types.Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or 'User'
    first_name = message.from_user.first_name or 'User'
    
    User.get_or_create(user_id, username, first_name)
    
    args = message.text.split()
    if len(args) > 1:
        referral_code = args[1]
        if referral_code.startswith('REF'):
            referrer = db.users.find_one({'referral_code': referral_code})
            if referrer and referrer['user_id'] != user_id:
                User.update_user(user_id, {'referred_by': referrer['user_id']})
                db.users.update_one(
                    {'user_id': referrer['user_id']},
                    {'$push': {'referrals': user_id}}
                )
    
    # UPDATED: Using web_app=WebAppInfo(...)
    # This opens the page INSIDE Telegram as a Mini App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎰 Open App', web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text='📊 My Stats', callback_data='my_stats')],
        [InlineKeyboardButton(text='👥 Referral', callback_data='referral')],
        [InlineKeyboardButton(text='ℹ️ Info', callback_data='raffle_info')]
    ])
    
    await message.answer(
        '🎰 Welcome to TON Raffle System!\n\n'
        '💰 Prize Pool: 100 TON\n'
        '🎟️ Max Tickets: 1000 (Limited)\n'
        '💵 Price: 0.5 TON per ticket\n'
        '👤 Max per person: 20 tickets\n'
        '✅ Draws when 700+ tickets sold\n\n'
        'Click "Open App" to start buying tickets!',
        reply_markup=keyboard
    )

@dp.callback_query(F.data == 'my_stats')
async def my_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = User.get_user(user_id)
    
    if not user:
        await callback.answer('User not found')
        return
    
    from models import Ticket, Raffle
    user_tickets = Ticket.count_user_tickets(user_id)
    raffle_stats = Raffle.get_raffle_stats()
    status = '✅ Draw can proceed!' if raffle_stats['is_ready_for_draw'] else f'⏳ Waiting for {raffle_stats["need_for_draw"]} more'
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎰 Open App', web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text='⬅️ Back', callback_data='back')]
    ])
    
    await callback.message.edit_text(
        f'📊 Your Statistics\n\n'
        f'💰 Balance: {user.get("balance", 0):.2f} TON\n'
        f'🎟️ Tickets Owned: {user_tickets}\n'
        f'💵 Total Spent: {user.get("total_spent", 0):.2f} TON\n'
        f'👥 Referrals: {len(user.get("referrals", []))}\n'
        f'💸 Referral Earnings: {user.get("referral_earnings", 0):.2f} TON\n\n'
        f'🎰 Raffle Status:\n'
        f'Sold: {raffle_stats["tickets_sold"]}/{raffle_stats["max_tickets"]}\n'
        f'{status}',
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == 'referral')
async def referral(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = User.get_user(user_id)
    
    if not user:
        await callback.answer('User not found')
        return
    
    bot_info = await bot.get_me()
    referral_link = f'https://t.me/{bot_info.username}?start={user["referral_code"]}'
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⬅️ Back', callback_data='back')]
    ])
    
    await callback.message.edit_text(
        f'👥 Your Referral Program\n\n'
        f'Your Code: `{user["referral_code"]}`\n\n'
        f'Earnings:\n'
        f'👥 Referrals: {len(user.get("referrals", []))}\n'
        f'💸 Total Earnings: {user.get("referral_earnings", 0):.2f} TON\n\n'
        f'💡 You earn 10% commission from your referrals!\n\n'
        f'Share this link: {referral_link}',
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    await callback.answer()

@dp.callback_query(F.data == 'raffle_info')
async def raffle_info(callback: types.CallbackQuery):
    from models import Raffle
    raffle_stats = Raffle.get_raffle_stats()
    status = '✅ Ready for Draw' if raffle_stats['is_ready_for_draw'] else '⏳ In Progress'
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎰 Open App', web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text='⬅️ Back', callback_data='back')]
    ])
    
    await callback.message.edit_text(
        f'📈 Raffle Information\n\n'
        f'💰 Prize Pool: 100 TON\n'
        f'🎟️ Tickets: {raffle_stats["tickets_sold"]}/{raffle_stats["max_tickets"]}\n'
        f'💵 Ticket Price: 0.5 TON\n'
        f'👤 Max per Person: 20\n\n'
        f'🎯 How it Works:\n'
        f'1️⃣ Buy tickets for 0.5 TON each\n'
        f'2️⃣ Each ticket has 6 random numbers (1-50)\n'
        f'3️⃣ When 700+ tickets sold, draw happens\n'
        f'4️⃣ Winners share the 100 TON prize!\n\n'
        f'Status: {status}',
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == 'back')
async def back(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎰 Open App', web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text='📊 My Stats', callback_data='my_stats')],
        [InlineKeyboardButton(text='👥 Referral', callback_data='referral')],
        [InlineKeyboardButton(text='ℹ️ Info', callback_data='raffle_info')]
    ])
    
    await callback.message.edit_text(
        '🎰 TON Raffle System\n\n'
        'Click "Open App" to start!',
        reply_markup=keyboard
    )
    await callback.answer()

@dp.message(Command('draw'))
async def draw_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer('❌ Unauthorized')
        return
    
    from models import Raffle, Ticket
    raffle_stats = Raffle.get_raffle_stats()
    
    if not raffle_stats['is_ready_for_draw']:
        await message.answer(f'❌ Not enough tickets. Need {raffle_stats["need_for_draw"]} more.')
        return
    
    await message.answer('🎰 Drawing raffle winners...')
    
    raffle = Raffle.get_active_raffle()
    all_tickets = list(db.tickets.find({'raffle_id': raffle['_id']}))
    
    winning_numbers = Ticket.generate_numbers()
    
    await message.answer(f'🎯 Winning Numbers: {", ".join(map(str, winning_numbers))}')
    
    winners = []
    for ticket in all_tickets:
        matches = len([n for n in ticket['numbers'] if n in winning_numbers])
        if matches >= 4:
            winners.append(ticket['user_id'])
    
    if not winners:
        await message.answer('❌ No winners! Prize rolls over to next raffle.')
        Raffle.finish_raffle([])
        return
    
    from config import PRIZE_POOL
    prize_per_winner = PRIZE_POOL / len(winners)
    
    for winner_id in winners:
        from models import User
        User.add_balance(winner_id, prize_per_winner)
        try:
            await bot.send_message(
                winner_id,
                f'🎉 Congratulations!\n\n'
                f'You won {prize_per_winner:.2f} TON!\n\n'
                f'Winning numbers: {", ".join(map(str, winning_numbers))}'
            )
        except Exception as e:
            logger.error(f'Could not notify user {winner_id}: {e}')
    
    Raffle.finish_raffle(winners)
    
    await message.answer(f'✅ Draw complete! {len(winners)} winner(s) found.')

async def main():
    logger.info('🤖 Bot is starting...')
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())