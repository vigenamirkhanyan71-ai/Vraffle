import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, ADMIN_ID, TICKET_PRICE, MAX_TICKETS_PER_USER, PRIZE_POOL
from models import User, Ticket, Raffle
from database import db
 



# --- CONFIGURATION ---
WEB_APP_URL = 'https://vraffle.vercel.app'
TON_WALLET_ADDRESS = 'UQBNaut8qxhFJC-ZqmEeU5ZBaNuyARJO1TUIOlRA6ZZRhYlZ'
GROUP_LINK = 'https://t.me/+o-R20lj8GIk3NDFi'
ADMIN_PASSWORD = 'Vigen21.'  # Change this to your admin password!      
NUM_WINNERS = 5
PRIZE_PER_WINNER = PRIZE_POOL / NUM_WINNERS
MAX_TX_ATTEMPTS = 3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Store user states, language preferences, and admin mode
user_states = {}
user_language = {}
admin_mode = {}  # Track who is in admin mode
awaiting_password = {}  # Track who is waiting to enter password
admin_user_id = None  # Store the admin user ID
tx_attempts = {}  # Track transaction attempts

# --- TRANSLATIONS ---
TRANSLATIONS = {
    'en': {
        'welcome': '🎰 Welcome to TON Raffle System!\n\n💰 Prize Pool: 100 TON\n🎟️ Max Tickets:       1000 (Limited)\n💵 Price:       0.5 TON per ticket\n👤 Max per person: 20 tickets\n✅ Draws when 700+ tickets sold\n\nChoose an option below:        ',
        'choose_language':     '🌍 Choose your language:\nПожалуйста, выберите язык:        ',
        'english':  'English',
        'russian': 'Русский',
        'buy_ticket': '🎟️ Buy Ticket',
        'my_tickets': '🎫 My Tickets',
        'tickets_left': '📊 Tickets Left',
        'information': 'ℹ️ Information',
        'back': '⬅️ Back',
        'main_menu': '🎰 TON Raffle System\n\nChoose an option below:  ',
        'max_tickets_reached': '❌ You have reached the maximum number of tickets (20)!\n\nWait for the next raffle to buy more tickets.',
        'buy_ticket_msg': '🎟️ Buy Ticket\n\n💵 Price:   {price} TON per ticket\n📊 You can buy 1-{available} tickets\n\nHow many tickets do you want to buy?\n(Reply with a number:        1-{available})',
        'invalid_quantity': '❌ Invalid quantity!        You can buy 1-{available} tickets.',
        'not_enough_tickets': '❌ Not enough tickets available!  Only {remaining} left.',
        'payment_info': '💳 Payment Information\n\n🎟️ Tickets:     {quantity}\n💵 Price per ticket: {price} TON\n💰 Total Amount: {total} TON\n\n⚠️ IMPORTANT - READ BEFORE BUYING:\n❌ YOU CANNOT REFUND THE TICKET\n❌ If you buy the ticket YOU CANNOT RETURN the tickets\n❌ All purchases are FINAL\n\n📬 Send {total} TON to:\n`{wallet}`\n\nAfter sending, reply with your transaction ID to confirm.',
        'enter_number': '❌ Please enter a valid number!    ',
        'tx_verification': '🔔 New Transaction Verification\n\n👤 User:   @{username} (ID: {user_id})\n🎟️ Tickets:  {quantity}\n💰 Amount: {total} TON\n📝 Transaction ID: `{tx_id}`\n\nPlease verify the transaction.',
        'confirm':        '✅ Confirm',
        'reject':  '❌ Reject',
        'tx_received': '✅ Transaction ID received:       `{tx_id}`\n\n⏳ Waiting for admin confirmation...\nYou will be notified once the transaction is verified.',
        'unauthorized': '❌ Unauthorized',
        'tx_confirmed': '✅ Transaction Confirmed!\n\n🎟️ You purchased {quantity} tickets:\n\n{tickets}\n\n🔒 Your tickets are NON-REFUNDABLE!\n\n🔒 Hold your tickets and wait until the raffle starts!\n\n📢 Join our group to see when winners are announced:        ',
        'join_group':      '📢 Join Group',
        'main_menu_btn':  '🎰 Main Menu',
        'ticket_format':  '🎫 Ticket {num}:        {numbers}',
        'no_tickets':       '📭 You don\'t have any tickets yet!\n\nBuy tickets to participate in the raffle.',
        'your_tickets':  '🎫 Your Tickets ({current}/{max})\n\n{tickets}\n\n🔒 Hold your tickets and wait for the raffle draw!       ',
        'tickets_available': '📊 Tickets Available\n\n🎟️ Sold:       {sold}/1000\n📈 Left:   {remaining}\n\nProgress:  [{progress}]\n\nStatus: {status}',
        'ready_for_draw': '✅ Ready for Draw!        ',
        'need_more':        '⏳ Need {need} more',
        'raffle_info': '''ℹ️ Raffle Information

💰 Prize Pool: {pool} TON
🎟️ Ticket Price: {price} TON
📊 Total Tickets: 1000
👤 Max per Person: {max_per}

🎯 Prize Distribution:  
🏆 {num_winners} WINNING TICKETS will be randomly generated
💵 Prize per Winner: {prize_per_winner} TON (20% each)
📊 All 5 winners share the 100 TON prize equally

🎲 How the Raffle Works:
1️⃣ Each ticket has 6 random numbers (1-50)
2️⃣ When 700+ tickets sold, the draw happens
3️⃣ System randomly generates 5 COMPLETE WINNING TICKETS (5 sets of 6 numbers)
4️⃣ Users whose tickets EXACTLY MATCH any of the 5 winning tickets WIN
5️⃣ Winners receive 20 TON each (100 TON ÷ 5 winners)

🔒 TICKET POLICY:  
❌ All tickets are NON-REFUNDABLE
❌ No refunds after purchase
❌ Once bought, you CANNOT return tickets
❌ All purchases are FINAL

✅ FAIRNESS GUARANTEE:  
🎲 5 winning tickets generated completely at random
🎲 Each winning ticket has 6 random numbers (1-50)
🎲 Winners selected 100% by chance
🎲 No manual selection or bias
🎲 System automatically draws 5 winning tickets
🎲 Your ticket either matches or doesn't - no favoritism
🎲 Transparent process verified by all winners in our group

📢 Follow our group for live drawing & announcements:''',
        'not_enough_for_draw': '❌ Not enough tickets.        Need {need} more.',
        'drawing':        '🎰 Drawing raffle winners..     .',
        'winning_tickets': '🎯 Winning Tickets Generated:\n\n{tickets}',
        'no_winners': '❌ No winners!        Prize rolls over to next raffle.',
        'draw_complete': '✅ Draw complete!    {count} winner(s) found.\n\nEach winner receives:        {prize_per_winner} TON',
        'congratulations': '🎉 Congratulations!\n\nYou won {amount} TON!        🎊\n\nYour Winning Ticket Numbers:       {numbers}\n\n📢 Winners announced in our group:  ',
        'tx_rejected': '❌ Your transaction was rejected by admin.\n\nTransaction ID: `{tx_id}`\n\nPlease contact admin for more information or try again.',
        'tx_attempts_left': '❌ Invalid transaction ID!\n\n⏳ You have {attempts} attempts left.\n\nPlease send a valid transaction ID:   ',
        'tx_max_attempts': '❌ You have exceeded the maximum transaction attempts (3).\n\nPlease contact admin or try again later.',
        'admin_password_prompt': '🔐 Enter admin password:       ',
        'admin_password_wrong': '❌ Wrong password!  Access denied.\n\nType /client to switch to client mode.',
        'admin_mode_on': '✅ Admin Mode Activated!\n\n👨‍💼 You are now in Admin Mode\n\nYou will receive transaction verification messages.\n\nType /client to switch to client mode.',
        'client_mode_on': '✅ Client Mode Activated!\n\nYou can now buy tickets.\n\nType /admin to switch to admin mode.',
        'admin_panel':    '👨‍💼 Admin Panel Active\n\nWaiting for transaction verifications...\n\nYou will see verification messages when users send transaction IDs.\n\nType /client to switch to client mode.',
        'admin_panel_buttons': '👨‍💼 Admin Panel\n\nSelect an option:  ',
        'view_tickets_left': '📊 Tickets Left:    {left}/1000 ({sold} sold)\n\nStatus: {status}',
        'all_tickets_list': '🎟️ All Bought Tickets\n\n{tickets_info}\n\nTotal Tickets Sold: {total}',
        'no_tickets_sold': '📭 No tickets sold yet.',
        'admin_tx_confirmed': '✅ Transaction Confirmed!\n\n👤 User ID: {user_id}\n🎟️ Tickets Purchased: {quantity}\n💰 Total Amount: {total_price} TON\n\n📋 Ticket Details:\n{tickets_codes}\n\n✅ Confirmed and tickets generated!  ',
    },
    'ru': {
        'welcome': '🎰 Добро пожаловать в систему лотереи TON!\n\n💰 Призовой фонд: 100 TON\n🎟️ Максимум билетов:     1000 (Ограничено)\n💵 Цена:      0. 5 TON за билет\n👤 Максимум на человека: 20 билетов\n✅ Розыгрыш при 700+ проданных билетов\n\nВыберите опцию ниже:       ',
        'choose_language':   '🌍 Выберите язык:\nPlease choose your language:      ',
        'english': 'English',
        'russian':        'Русский',
        'buy_ticket': '🎟️ Купить билет',
        'my_tickets': '🎫 Мои билеты',
        'tickets_left': '📊 Осталось билетов',
        'information': 'ℹ️ Информация',
        'back':        '⬅️ Назад',
        'main_menu': '🎰 Система лотереи TON\n\nВыберите опцию ниже:   ',
        'max_tickets_reached': '❌ Вы достигли максимального количества билетов (20)!\n\nДождитесь следующей лотереи, чтобы купить еще билеты.',
        'buy_ticket_msg': '🎟️ Купить билет\n\n💵 Цена: {price} TON за билет\n📊 Вы можете купить 1-{available} билетов\n\nСколько билетов вы хотите купить?\n(Ответьте числом:       1-{available})',
        'invalid_quantity':   '❌ Неверное количество!        Вы можете купить 1-{available} билетов.',
        'not_enough_tickets': '❌ Недостаточно доступных билетов!  Осталось только {remaining}.',
        'payment_info':   '💳 Информация о платеже\n\n🎟️ Билеты:       {quantity}\n💵 Цена за билет: {price} TON\n💰 Общая сумма: {total} TON\n\n⚠️ ВАЖНО - ПРОЧИТАЙТЕ ПЕРЕД ПОКУПКОЙ:\n❌ ВЫ НЕ СМОЖЕТЕ ВЕРНУТЬ БИЛЕТ\n❌ Если вы купите билет, ВЫ НЕ МОЖЕТЕ ВЕРНУТЬ билеты\n❌ Все покупки ОКОНЧАТЕЛЬНЫ\n\n📬 Отправьте {total} TON на:\n`{wallet}`\n\nПосле отправки ответьте своим ID транзакции для подтверждения.',
        'enter_number': '❌ Пожалуйста, введите правильное число!        ',
        'tx_verification':   '🔔 Новая проверка транзакции\n\n👤 Пользователь:  @{username} (ID: {user_id})\n🎟️ Билеты: {quantity}\n💰 Сумма: {total} TON\n📝 ID транзакции: `{tx_id}`\n\nПожалуйста, проверьте транзакцию.',
        'confirm':       '✅ Подтвердить',
        'reject':  '❌ Отклонить',
        'tx_received': '✅ ID транзакции получен:      `{tx_id}`\n\n⏳ Ожидание подтверждения администратором...\nВы будете уведомлены после проверки транзакции.',
        'unauthorized': '❌ Не авторизовано',
        'tx_confirmed': '✅ Транзакция подтверждена!\n\n🎟️ Вы купили {quantity} билетов:\n\n{tickets}\n\n🔒 Ваши билеты НЕ ВОЗВРАЩАЕМЫЕ!\n\n🔒 Держите свои билеты и ждите начала лотереи!\n\n📢 Присоединитесь к нашей группе, чтобы узнать, когда будут объявлены победители:        ',
        'join_group':   '📢 Присоединиться к группе',
        'main_menu_btn': '🎰 Главное меню',
        'ticket_format': '🎫 Билет {num}:       {numbers}',
        'no_tickets': '📭 У вас еще нет билетов!\n\nКупите билеты, чтобы участвовать в лотерее.',
        'your_tickets':   '🎫 Ваши билеты ({current}/{max})\n\n{tickets}\n\n🔒 Держите свои билеты и ждите розыгрыша!     ',
        'tickets_available':   '📊 Доступные билеты\n\n🎟️ Продано: {sold}/1000\n📈 Осталось:   {remaining}\n\nПрогресс:    [{progress}]\n\nСтатус:    {status}',
        'ready_for_draw': '✅ Готово к розыгрышу!        ',
        'need_more':       '⏳ Нужно еще {need}',
        'raffle_info':  '''ℹ️ Информация о лотерее

💰 Призовой фонд: {pool} TON
🎟️ Цена билета: {price} TON
📊 Всего билетов: 1000
👤 Максимум на человека: {max_per}

🎯 Распределение призов:  
🏆 Будут случайно сгенерированы {num_winners} ВЫИГРЫШНЫХ БИЛЕТОВ
💵 Приз за победителя: {prize_per_winner} TON (20% каждый)
📊 Все 5 победителей делят 100 TON поровну

🎲 Как работает лотерея:   
1️⃣ Каждый билет имеет 6 случайных чисел (1-50)
2️⃣ При продаже 700+ билетов начинается розыгрыш
3️⃣ Система случайно генерирует 5 ПОЛНЫХ ВЫИГРЫШНЫХ БИЛЕТОВ (5 наборов по 6 чисел)
4️⃣ Пользователи, чьи билеты ТОЧНО СОВПАДАЮТ с одним из 5 выигрышных билетов, ВЫИГРЫВАЮТ
5️⃣ Победители получают по 20 TON (100 TON ÷ 5 победителей)

🔒 ПОЛИТИКА БИЛЕТОВ:  
❌ Все билеты НЕ ВОЗВРАЩАЕМЫЕ
❌ Возвраты не производятся после покупки
❌ После покупки билеты НЕЛЬЗЯ ВЕРНУТЬ
❌ Все покупки ОКОНЧАТЕЛЬНЫ

✅ ГАРАНТИЯ ЧЕСТНОСТИ:  
🎲 5 выигрышных билетов генерируются полностью случайно
🎲 Каждый выигрышный билет имеет 6 случайных чисел (1-50)
🎲 Победители выбираются 100% случайно
🎲 Никакого ручного выбора или предвзятости
🎲 Система автоматически генерирует 5 выигрышных билетов
🎲 Ваш билет либо совпадает, либо нет - никакого фаворитизма
🎲 Прозрачный процесс, проверенный всеми победителями в нашей группе

📢 Следите за нашей группой для прямого розыгрыша и объявлений:       ''',
        'not_enough_for_draw': '❌ Недостаточно билетов.        Нужно еще {need}.',
        'drawing':       '🎰 Проведение розыгрыша..      .',
        'winning_tickets':   '🎯 Сгенерированы выигрышные билеты:\n\n{tickets}',
        'no_winners': '❌ Нет победителей!       Приз переходит в следующую лотерею.',
        'draw_complete': '✅ Розыгрыш завершен!   Найдено {count} победитель(ей).\n\nКаждый победитель получает:      {prize_per_winner} TON',
        'congratulations':   '🎉 Поздравляем!\n\nВы выиграли {amount} TON!        🎊\n\nНомера вашего выигрышного билета: {numbers}\n\n📢 Победители объявлены в нашей группе:     ',
        'tx_rejected':   '❌ Ваша транзакция отклонена администратором.\n\nID транзакции: `{tx_id}`\n\nПожалуйста, свяжитесь с администратором для получения дополнительной информации или повторите попытку.',
        'tx_attempts_left': '❌ Неверный ID транзакции!\n\n⏳ У вас осталось {attempts} попыток.\n\nПожалуйста, отправьте действительный ID транзакции:   ',
        'tx_max_attempts': '❌ Вы превысили максимальное количество попыток транзакции (3).\n\nПожалуйста, свяжитесь с администратором или попробуйте позже.',
        'admin_password_prompt': '🔐 Введите пароль администратора:     ',
        'admin_password_wrong': '❌ Неверный пароль!    Доступ запрещен.\n\nВведите /client чтобы перейти в режим клиента.',
        'admin_mode_on': '✅ Режим администратора активирован!\n\n👨‍💼 Вы теперь в режиме администратора\n\nВы будете получать сообщения с подтверждением транзакций.\n\nВведите /client чтобы перейти в режим клиента.',
        'client_mode_on': '✅ Режим клиента активирован!\n\nВы можете теперь покупать билеты.\n\nВведите /admin чтобы перейти в режим администратора.',
        'admin_panel':    '👨‍💼 Панель администратора активна\n\nОжидание проверки транзакций...\n\nВы будете видеть сообщения с подтверждением, когда пользователи отправляют ID транзакций.\n\nВведите /client чтобы перейти в режим клиента.',
        'admin_panel_buttons': '👨‍💼 Панель администратора\n\nВыберите опцию: ',
        'view_tickets_left':   '📊 Осталось билетов:    {left}/1000 ({sold} продано)\n\nСтатус:    {status}',
        'all_tickets_list':  '🎟️ Все купленные билеты\n\n{tickets_info}\n\nВсего продано билетов: {total}',
        'no_tickets_sold': '📭 Билеты еще не проданы.',
        'admin_tx_confirmed': '✅ Транзакция подтверждена!\n\n👤 ID пользователя: {user_id}\n🎟️ Куплено билетов: {quantity}\n💰 Общая сумма: {total_price} TON\n\n📋 Детали билетов:\n{tickets_codes}\n\n✅ Подтверждено и билеты созданы! ',
    }
}

def get_text(lang, key, **kwargs):
    """Get translated text with format parameters"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return text.format(**kwargs) if kwargs else text

@dp.message(Command('start'))
async def start_command(message:   types.Message):
    """Handle /start command - Choose language"""
    user_id = message.  from_user.id
    admin_mode[user_id] = False
    awaiting_password[user_id] = False
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🇬🇧 English', callback_data='lang_en')],
        [InlineKeyboardButton(text='🇷🇺 Русский', callback_data='lang_ru')]
    ])
    
    await message.answer(
        get_text('en', 'choose_language'),
        reply_markup=keyboard
    )

@dp.message(Command('admin'))
async def admin_command(message:  types.Message):
    """Request admin password"""
    user_id = message.from_user.id
    lang = user_language.   get(user_id, 'en')
    
    awaiting_password[user_id] = True
    await message.answer(get_text(lang, 'admin_password_prompt'))

@dp.message(Command('client'))
async def client_command(message:   types.Message):
    """Switch to client mode"""
    user_id = message.from_user.   id
    lang = user_language.  get(user_id, 'en')
    
    admin_mode[user_id] = False
    awaiting_password[user_id] = False
    
    await message.answer(get_text(lang, 'client_mode_on'))

@dp.message(F.text)
async def handle_password(message: types.Message):
    """Handle admin password entry"""
    global admin_user_id
    user_id = message.from_user.id
    lang = user_language.get(user_id, 'en')
    
    # Check if user is waiting for password
    if awaiting_password.   get(user_id, False):
        password = message.text.strip()
        
        if password == ADMIN_PASSWORD:
            admin_mode[user_id] = True
            admin_user_id = user_id
            awaiting_password[user_id] = False
            
            await message.answer(get_text(lang, 'admin_mode_on'))
            
            # Show admin panel buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='📊 Tickets Left', callback_data='admin_tickets_left')],
                [InlineKeyboardButton(text='🎟️ All Tickets', callback_data='admin_all_tickets')]
            ])
            await message. answer(get_text(lang, 'admin_panel_buttons'), reply_markup=keyboard)
        else:
            await message.answer(get_text(lang, 'admin_password_wrong'))
            awaiting_password[user_id] = False
        return

    # Only process ticket quantity if in client mode and awaiting quantity
    if not admin_mode.  get(user_id, False) and user_id in user_states and user_states[user_id].   get('action') == 'awaiting_quantity':
        try:  
            quantity = int(message.  text)
            user = User.  get_user(user_id)
            current_tickets = Ticket.  count_user_tickets(user_id)
            tickets_available = MAX_TICKETS_PER_USER - current_tickets
            raffle_stats = Raffle. get_raffle_stats()
            
            if quantity < 1 or quantity > tickets_available:  
                await message.answer(
                    get_text(lang, 'invalid_quantity', available=tickets_available)
                )
                return
            
            if quantity > raffle_stats['remaining']:   
                await message.answer(
                    get_text(lang, 'not_enough_tickets', remaining=raffle_stats['remaining'])
                )
                return
            
            total_price = quantity * TICKET_PRICE
            user_states[user_id] = {
                'action': 'awaiting_payment',
                'quantity': quantity,
                'total_price': total_price
            }
            tx_attempts[user_id] = 0  # Reset attempts
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text(lang, 'back'), callback_data='back')]
            ])
            
            await message.answer(
                get_text(lang, 'payment_info',
                         quantity=quantity,
                         price=TICKET_PRICE,
                         total=total_price,
                         wallet=TON_WALLET_ADDRESS),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except ValueError:
            await message.  answer(get_text(lang, 'enter_number'))
        return

    # Only process transaction ID if in client mode and awaiting payment
    if not admin_mode.  get(user_id, False) and user_id in user_states and user_states[user_id].get('action') == 'awaiting_payment':
        tx_id = message.text.strip()
        quantity = user_states[user_id]['quantity']
        total_price = user_states[user_id]['total_price']
        username = message.from_user.username or 'unknown'
        
        # Track attempts
        if user_id not in tx_attempts:
            tx_attempts[user_id] = 0
        
        tx_attempts[user_id] += 1
        remaining_attempts = MAX_TX_ATTEMPTS - tx_attempts[user_id]
        
        logger.info(f'✅ Processing transaction for user {user_id}:   TX={tx_id}, Attempt {tx_attempts[user_id]}/{MAX_TX_ATTEMPTS}')
        
        # Send to admin (only if admin is in admin mode)
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text('en', 'confirm'), callback_data=f'confirm_tx_{user_id}_{tx_id}'),
                InlineKeyboardButton(text=get_text('en', 'reject'), callback_data=f'reject_tx_{user_id}_{tx_id}')
            ]
        ])
        
        try:
            if admin_user_id:   
                await bot.send_message(
                    admin_user_id,
                    get_text('en', 'tx_verification',
                             username=username,
                             user_id=user_id,
                             quantity=quantity,
                             total=total_price,
                             tx_id=tx_id),
                    reply_markup=admin_keyboard,
                    parse_mode='Markdown'
                )
                logger.info(f'✅ Admin notification sent to {admin_user_id}')
            else:
                logger.warning(f'⚠️ No admin logged in to receive verification')
        except Exception as e:  
            logger.error(f'❌ Failed to send admin notification: {e}')
        
        # Inform client
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, 'back'), callback_data='back')]
        ])
        
        if remaining_attempts > 0:
            await message.answer(
                get_text(lang, 'tx_received', tx_id=tx_id),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            # Max attempts reached
            await message.answer(get_text(lang, 'tx_max_attempts'))
            user_states[user_id] = {'action': 'awaiting_quantity'}
            tx_attempts[user_id] = 0
            return
        
        logger.info(f'✅ Client message sent to {user_id}')
        
        user_states[user_id] = {
            'action': 'awaiting_confirmation',
            'quantity': quantity,
            'total_price': total_price,
            'tx_id': tx_id
        }

@dp.callback_query(F.data.startswith('lang_'))
async def set_language(callback: types.CallbackQuery):
    """Set user language preference"""
    user_id = callback.from_user.id
    lang = callback.data.split('_')[1]
    user_language[user_id] = lang
    
    username = callback.from_user.username or 'User'
    first_name = callback.from_user.first_name or 'User'
    
    User.get_or_create(user_id, username, first_name)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'buy_ticket'), callback_data='buy_ticket')],
        [InlineKeyboardButton(text=get_text(lang, 'my_tickets'), callback_data='my_tickets')],
        [InlineKeyboardButton(text=get_text(lang, 'tickets_left'), callback_data='tickets_left')],
        [InlineKeyboardButton(text=get_text(lang, 'information'), callback_data='information')],
        [InlineKeyboardButton(text='🇬🇧 ' + get_text(lang, 'english'), callback_data='lang_en'),
         InlineKeyboardButton(text='🇷🇺 ' + get_text(lang, 'russian'), callback_data='lang_ru')]
    ])
    
    await callback.message.edit_text(
        get_text(lang, 'welcome'),
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == 'buy_ticket')
async def buy_ticket_start(callback: types.CallbackQuery):
    """Start ticket purchase process"""
    user_id = callback.from_user.id
    lang = user_language.   get(user_id, 'en')
    
    if admin_mode.get(user_id, False):
        await callback.   answer('You are in Admin Mode. Type /client to buy tickets.    ', show_alert=True)
        return
    
    user_states[user_id] = {'action': 'awaiting_quantity'}
    
    user = User.get_user(user_id)
    current_tickets = Ticket.count_user_tickets(user_id)
    tickets_available = MAX_TICKETS_PER_USER - current_tickets
    
    if tickets_available <= 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, 'back'), callback_data='back')]
        ])
        await callback.message.edit_text(
            get_text(lang, 'max_tickets_reached'),
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'back'), callback_data='back')]
    ])
    
    await callback.message.edit_text(
        get_text(lang, 'buy_ticket_msg',
                 price=TICKET_PRICE,
                 available=tickets_available),
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == 'my_tickets')
async def my_tickets(callback: types.CallbackQuery):
    """Show user's tickets"""
    user_id = callback.from_user.id
    lang = user_language.   get(user_id, 'en')
    
    if admin_mode.get(user_id, False):
        await callback.   answer('You are in Admin Mode.     Type /client to view tickets.', show_alert=True)
        return
    
    raffle = Raffle.get_active_raffle()
    user_tickets = Ticket.get_user_tickets(user_id, raffle['_id'])
    
    if not user_tickets:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, 'back'), callback_data='back')]
        ])
        
        await callback.message.edit_text(
            get_text(lang, 'no_tickets'),
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    ticket_list = '\n'.join([
        get_text(lang, 'ticket_format', num=i+1, numbers=', '.join(map(str, t['numbers'])))
        for i, t in enumerate(user_tickets)
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'back'), callback_data='back')]
    ])
    
    await callback.  message.edit_text(
        get_text(lang, 'your_tickets',
                 current=len(user_tickets),
                 max=MAX_TICKETS_PER_USER,
                 tickets=ticket_list),
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.   data == 'tickets_left')
async def tickets_left(callback: types.CallbackQuery):
    """Show tickets remaining"""
    user_id = callback.  from_user.id
    lang = user_language.  get(user_id, 'en')
    
    if admin_mode.  get(user_id, False):
        await callback.  answer('You are in Admin Mode.   Type /client to view tickets.', show_alert=True)
        return
    
    raffle_stats = Raffle.get_raffle_stats()
    
    progress_bar = '█' * (raffle_stats['tickets_sold'] // 50) + '░' * ((1000 - raffle_stats['tickets_sold']) // 50)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'back'), callback_data='back')]
    ])
    
    status = get_text(lang, 'ready_for_draw') if raffle_stats['is_ready_for_draw'] else get_text(lang, 'need_more', need=raffle_stats['need_for_draw'])
    
    await callback.  message.edit_text(
        get_text(lang, 'tickets_available',
                 sold=raffle_stats['tickets_sold'],
                 remaining=raffle_stats['remaining'],
                 progress=progress_bar,
                 status=status),
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == 'information')
async def information(callback:    types.CallbackQuery):
    """Show raffle information"""
    user_id = callback.from_user.id
    lang = user_language.   get(user_id, 'en')
    
    if admin_mode.get(user_id, False):
        await callback.   answer('You are in Admin Mode.     Type /client to view information.', show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'back'), callback_data='back')],
        [InlineKeyboardButton(text=get_text(lang, 'join_group'), url=GROUP_LINK)]
    ])
    
    await callback.message.edit_text(
        get_text(lang, 'raffle_info',
                 pool=PRIZE_POOL,
                 price=TICKET_PRICE,
                 max_per=MAX_TICKETS_PER_USER,
                 num_winners=NUM_WINNERS,
                 prize_per_winner=PRIZE_PER_WINNER),
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.  data == 'back')
async def back_to_menu(callback: types.CallbackQuery):
    """Go back to main menu"""
    user_id = callback.from_user.id
    lang = user_language.get(user_id, 'en')
    
    if admin_mode.get(user_id, False):
        await callback.  answer('You are in Admin Mode.   Type /client to go back.    ', show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'buy_ticket'), callback_data='buy_ticket')],
        [InlineKeyboardButton(text=get_text(lang, 'my_tickets'), callback_data='my_tickets')],
        [InlineKeyboardButton(text=get_text(lang, 'tickets_left'), callback_data='tickets_left')],
        [InlineKeyboardButton(text=get_text(lang, 'information'), callback_data='information')],
        [InlineKeyboardButton(text='🇬🇧 English', callback_data='lang_en'),
         InlineKeyboardButton(text='🇷🇺 Русский', callback_data='lang_ru')]
    ])
    
    await callback.message.edit_text(
        get_text(lang, 'main_menu'),
        reply_markup=keyboard
    )
    await callback.  answer()

@dp.callback_query(F.data == 'admin_tickets_left')
async def admin_tickets_left(callback:   types.CallbackQuery):
    """Show tickets left in admin panel"""
    user_id = callback.from_user.id
    
    if not admin_mode.get(user_id, False):
        await callback.answer('You must be in Admin Mode', show_alert=True)
        return
    
    raffle_stats = Raffle.  get_raffle_stats()
    status = get_text('en', 'ready_for_draw') if raffle_stats['is_ready_for_draw'] else get_text('en', 'need_more', need=raffle_stats['need_for_draw'])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📊 Tickets Left', callback_data='admin_tickets_left')],
        [InlineKeyboardButton(text='🎟️ All Tickets', callback_data='admin_all_tickets')]
    ])
    
    await callback.message.edit_text(
        get_text('en', 'view_tickets_left',
                 left=raffle_stats['remaining'],
                 sold=raffle_stats['tickets_sold'],
                 status=status),
        reply_markup=keyboard
    )
    await callback.   answer()

@dp.callback_query(F.data == 'admin_all_tickets')
async def admin_all_tickets(callback:  types.CallbackQuery):
    """Show all bought tickets - only user ID and tickets"""
    user_id = callback.from_user.id
    
    if not admin_mode. get(user_id, False):
        await callback.answer('You must be in Admin Mode', show_alert=True)
        return
    
    raffle = Raffle.get_active_raffle()
    all_tickets = list(db.tickets.find({'raffle_id': raffle['_id']}))
    
    if not all_tickets:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='📊 Tickets Left', callback_data='admin_tickets_left')],
            [InlineKeyboardButton(text='🎟️ All Tickets', callback_data='admin_all_tickets')]
        ])
        await callback.  message.edit_text(
            get_text('en', 'no_tickets_sold'),
            reply_markup=keyboard
        )
        await callback.  answer()
        return
    
    # Build tickets info - ONLY User ID and tickets, NO usernames
    tickets_info = []
    for ticket in all_tickets:
        user_id_display = ticket['user_id']
        numbers = ', '.join(map(str, ticket['numbers']))
        tickets_info.append(f"👤 ID: {user_id_display} | {numbers}")
    
    tickets_display = '\n'.join(tickets_info[:   50])  # Show max 50 tickets per message
    
    if len(tickets_info) > 50:
        tickets_display += f"\n\n... and {len(tickets_info) - 50} more tickets"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📊 Tickets Left', callback_data='admin_tickets_left')],
        [InlineKeyboardButton(text='🎟️ All Tickets', callback_data='admin_all_tickets')]
    ])
    
    await callback.message.edit_text(
        get_text('en', 'all_tickets_list',
                 tickets_info=tickets_display,
                 total=len(all_tickets)),
        reply_markup=keyboard
    )
    await callback.  answer()

@dp.callback_query(F.data.   startswith('confirm_tx_'))
async def confirm_transaction(callback: types.CallbackQuery):
    """Admin confirms transaction"""
    user_id = callback.from_user.id
    
    if not admin_mode.get(user_id, False):
        await callback.answer('You must be in Admin Mode', show_alert=True)
        return
    
    parts = callback.data.split('_')
    customer_id = int(parts[2])
    tx_id = '_'.join(parts[3:])
    lang = user_language.  get(customer_id, 'en')
    
    if customer_id not in user_states:   
        await callback.answer('Transaction data not found', show_alert=True)
        return
    
    quantity = user_states[customer_id]['quantity']
    total_price = user_states[customer_id]['total_price']
    
    # Create tickets for user
    raffle = Raffle.get_active_raffle()
    tickets_created = []
    
    for _ in range(quantity):
        ticket = Ticket.   create_ticket(customer_id, raffle['_id'])
        tickets_created.append(ticket)
        Raffle.add_ticket(customer_id)
    
    # Update user balance and tracking
    User.add_balance(customer_id, 0)
    user_doc = db.users.find_one({'user_id': customer_id})
    User.update_user(customer_id, {'total_spent': user_doc.   get('total_spent', 0) + total_price})
    
    # Check if referrer exists and apply commission
    user = User.get_user(customer_id)
    if user. get('referred_by'):
        User.apply_referral(user['referred_by'], total_price)
    
    # Send ticket details to user
    ticket_details = '\n'.join([
        get_text(lang, 'ticket_format', num=i+1, numbers=', '.join(map(str, t['numbers'])))
        for i, t in enumerate(tickets_created)
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, 'main_menu_btn'), callback_data='back')],
        [InlineKeyboardButton(text=get_text(lang, 'join_group'), url=GROUP_LINK)]
    ])
    
    await bot.send_message(
        customer_id,
        get_text(lang, 'tx_confirmed', quantity=quantity, tickets=ticket_details),
        reply_markup=keyboard
    )
    
    # Show admin confirmation with ticket codes - ONLY user ID and tickets
    ticket_codes = '\n'.join([
        f"🎫 Ticket {i+1}: {', '.join(map(str, t['numbers']))}"
        for i, t in enumerate(tickets_created)
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📊 Tickets Left', callback_data='admin_tickets_left')],
        [InlineKeyboardButton(text='🎟️ All Tickets', callback_data='admin_all_tickets')]
    ])
    
    await callback.message.edit_text(
        get_text('en', 'admin_tx_confirmed',
                 user_id=customer_id,
                 quantity=quantity,
                 total_price=total_price,
                 tickets_codes=ticket_codes),
        reply_markup=keyboard
    )
    
    # Clear user state
    if customer_id in user_states:   
        del user_states[customer_id]
    if customer_id in tx_attempts:  
        del tx_attempts[customer_id]
    
    await callback.answer('✅ Transaction confirmed', show_alert=True)

@dp.callback_query(F.data.  startswith('reject_tx_'))
async def reject_transaction(callback: types.CallbackQuery):
    """Admin rejects transaction"""
    user_id = callback.from_user.id
    
    if not admin_mode.get(user_id, False):
        await callback.answer('You must be in Admin Mode', show_alert=True)
        return
    
    parts = callback.data.split('_')
    customer_id = int(parts[2])
    tx_id = '_'.join(parts[3:])
    lang = user_language. get(customer_id, 'en')
    
    # Notify user
    await bot.send_message(
        customer_id,
        get_text(lang, 'tx_rejected', tx_id=tx_id),
        parse_mode='Markdown'
    )
    
    # Notify admin
    await callback.message.edit_text(
        f'❌ Transaction rejected!\n\n'
        f'👤 Client:  {customer_id}\n'
        f'📝 Transaction ID: {tx_id}'
    )
    
    # Clear user state
    if customer_id in user_states:  
        del user_states[customer_id]
    if customer_id in tx_attempts: 
        del tx_attempts[customer_id]
    
    await callback.  answer('✅ Transaction rejected', show_alert=True)

@dp.message(Command('draw'))
async def draw_command(message: types.Message):
    """Admin draw raffle winners"""
    user_id = message.from_user.id
    
    if not admin_mode. get(user_id, False):
        await message.answer('You must be in Admin Mode to use this command')
        return
    
    raffle_stats = Raffle.get_raffle_stats()
    
    if not raffle_stats['is_ready_for_draw']:
        await message.answer(
            get_text('en', 'not_enough_for_draw', need=raffle_stats['need_for_draw'])
        )
        return
    
    await message.answer(get_text('en', 'drawing'))
    
    raffle = Raffle.get_active_raffle()
    all_tickets = list(db.tickets.find({'raffle_id':   raffle['_id']}))
    
    # Generate 5 complete winning tickets with 6 numbers each
    winning_tickets = []
    for i in range(NUM_WINNERS):
        winning_ticket = Ticket.generate_numbers()
        winning_tickets.append(winning_ticket)
    
    # Format winning tickets for display
    winning_display = '\n'.join([
        f"🎯 Winning Ticket {i+1}:       {', '.join(map(str, ticket))}"
        for i, ticket in enumerate(winning_tickets)
    ])
    
    await message.answer(
        get_text('en', 'winning_tickets', tickets=winning_display)
    )
    
    # Find winners - tickets that exactly match any of the 5 winning tickets
    winners = {}
    for ticket in all_tickets:
        for winning_idx, winning_ticket in enumerate(winning_tickets):
            if ticket['numbers'] == winning_ticket:  
                winners[ticket['user_id']] = {
                    'winning_numbers': winning_ticket,
                    'user_ticket':    ticket['numbers']
                }
                break
    
    if not winners:
        await message.   answer(get_text('en', 'no_winners'))
        Raffle.finish_raffle([])
        return
    
    prize_per_winner = PRIZE_POOL / NUM_WINNERS
    
    for winner_id, winner_info in winners.items():
        lang = user_language.get(winner_id, 'en')
        User.add_balance(winner_id, prize_per_winner)
        try:
            await bot.send_message(
                winner_id,
                get_text(lang, 'congratulations',
                         amount=f'{prize_per_winner:.2f}',
                         numbers=', '.join(map(str, winner_info['user_ticket']))),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=get_text(lang, 'join_group'), url=GROUP_LINK)]
                ])
            )
        except Exception as e:  
            logger.error(f'Could not notify user {winner_id}: {e}')
    
    Raffle.finish_raffle(list(winners.keys()))
    
    await message.answer(
        get_text('en', 'draw_complete', count=len(winners), prize_per_winner=f'{prize_per_winner:.2f}')
    )

async def main():
    logger.info('🤖 Bot is starting.. .')
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())



