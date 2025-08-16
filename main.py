import os
from dotenv import load_dotenv
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Import your roulette logic
from roulette import spin_wheel, determine_outcome, ROULETTE_NUMBERS
from blackjack import BlackjackGame

# --- Constants ---
VALID_ROULETTE_BETS = (
    list(set(ROULETTE_NUMBERS.values())) +  # red, black, green
    [str(i) for i in range(37)] +           # 0-36
    ["odd", "even", "high", "low", "1st12", "2nd12", "3rd12", "col1", "col2", "col3"]
)


# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
if TOKEN is None:
    print("Error: TELEGRAM_TOKEN not found in environment variables or .env file.")
    exit(1)

# In-memory stores for player data (for simplicity, consider a database for persistence)
user_balances = {}       # {user_id: balance}
active_blackjack_games = {}  # {user_id: BlackjackGame_instance}

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with the main game menu."""
    keyboard = [
        [InlineKeyboardButton("Roulette 🎡", callback_data='menu_roulette')],
        [InlineKeyboardButton("Blackjack ♠️", callback_data='menu_blackjack')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Bienvenido al Casino! Elige un juego para jugar:", reply_markup=reply_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 1000 # Give new users a starting balance
        await update.message.reply_text(f"¡Bienvenido! He creado una cuenta para ti con un saldo inicial de 1000.")

    await games_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    help_text = (
        "<b>--- Comandos Generales ---</b>\n\n"
        "<b>/start</b> - Inicializa tu cuenta\n"
        "<b>/games</b> - Muestra el menú principal de juegos\n"
        "<b>/balance</b> - Consulta tu saldo actual\n\n"
        "<b>--- Ruleta ---</b>\n\n"
        "<b>/roulette &lt;cantidad&gt; &lt;tipo&gt;</b> - Realiza una apuesta y gira la ruleta (ej: <code>/roulette 10 rojo</code>)\n\n"
        "<b>--- Blackjack ---</b>\n\n"
        "<b>/blackjack &lt;cantidad&gt;</b> - Comienza un nuevo juego de Blackjack\n\n"
        "Durante una partida de Blackjack, usa los botones <b>Pedir</b> y <b>Plantarse</b> en lugar de los comandos."
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Realiza una apuesta e inmediatamente gira la ruleta."""
    user_id = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /roulette <cantidad> <tipo> (ej: /roulette 10 rojo)")
        return

    try:
        bet_type_translations = {
            "rojo": "red", "negro": "black", "verde": "green",
            "par": "even", "impar": "odd",
            "alto": "high", "bajo": "low",
            "1ra12": "1st12", "2da12": "2nd12", "3ra12": "3rd12",
        }
        bet_amount = int(context.args[0])
        raw_bet_type = context.args[1].lower()
        bet_type = bet_type_translations.get(raw_bet_type, raw_bet_type) # Translate if found
    except ValueError:
        await update.message.reply_text("Cantidad inválida. Por favor, introduce un número.")
        return #Mensaje de cantidad invalida

    if bet_amount <= 0:
        await update.message.reply_text("La cantidad de la apuesta debe ser positiva.")
        return
    if user_id not in user_balances or user_balances[user_id] < bet_amount:
        await update.message.reply_text(f"¡No tienes saldo suficiente! Tu saldo es: {user_balances.get(user_id, 0)}")
        return # Traducir los mensajes de error

    # Validate the canonical (English) bet type
    if bet_type not in VALID_ROULETTE_BETS:
        await update.message.reply_text(
            f"Tipo de apuesta inválido: '{raw_bet_type}'.\n"
            "Por favor, usa un número (0-36), un color (rojo/negro/verde), "
            "o tipos comunes (par/impar, alto/bajo, 1ra12, col1, etc.)."
        )
        return

    # Perform the spin immediately
    winning_number = spin_wheel()
    winning_color = ROULETTE_NUMBERS[winning_number]
    color_emoji = "🟢" if winning_color == "green" else ("🔴" if winning_color == "red" else "⚫")

    outcome = determine_outcome(winning_number, bet_amount, bet_type)
    user_balances[user_id] += outcome
    new_balance = user_balances[user_id]

    if outcome > 0:
        win_messages = [
            f"🎉 ¡Cha-ching! ¡GANASTE {outcome}! Tu billetera ahora está más gorda: 💰 {new_balance}",
            f"¡SÍ! ¡La ruleta te favorece! Unos geniales {outcome} créditos son tuyos. Nuevo balance: 💰 {new_balance}",
            f"🥳 ¡Ganador, ganador, cena de pollo! ¡Has ganado {outcome}! Balance total: 💰 {new_balance}",
        ]
        message = (
            f"Girando la ruleta... 🎡\n"
            f"La bola ha caído en: {color_emoji} {winning_number}!\n\n"
            f"{random.choice(win_messages)}" # Traducir los mensajes de victoria
        )
    else:
        loss_messages = [
            f"Vaya. La casa gana esta vez. Has perdido {abs(outcome)}. Tu saldo ahora es: 💰 {new_balance}",
            f"¡Casi! La suerte no está de tu lado. Has perdido {abs(outcome)}. Saldo restante: 💰 {new_balance}",
            f"Esta vez no pudo ser. La ruleta no giró a tu favor. Has perdido {abs(outcome)}. Te quedan 💰 {new_balance}.",
        ]
        message = (
            f"Girando la ruleta... 🎡\n"
            f"La bola ha caído en: {color_emoji} {winning_number}.\n\n"
            f"😔 {random.choice(loss_messages)}" # Traducir los mensajes de derrota
        )

    await update.message.reply_text(message)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_balance = user_balances.get(user_id, 0) # Traducir el mensaje de balance
    await update.message.reply_text(f"Tu saldo actual es: {current_balance}")


async def blackjack_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comienza un nuevo juego de blackjack."""
    user_id = update.effective_user.id

    if user_id in active_blackjack_games:
        await update.message.reply_text("Ya tienes un juego en progreso. ¡Por favor, termínalo antes de comenzar uno nuevo!")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Uso: /blackjack <cantidad>")
        return

    try:
        bet_amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Cantidad inválida. Por favor, introduce un número.")
        return

    if bet_amount <= 0:
        await update.message.reply_text("Bet amount must be positive.")
        return

    if user_id not in user_balances or user_balances[user_id] < bet_amount:
        await update.message.reply_text(f"¡No tienes saldo suficiente! Tu saldo es: {user_balances.get(user_id, 0)}")
        return

    # Create and store the game
    game = BlackjackGame(bet_amount)
    game.start_game()
    active_blackjack_games[user_id] = game

    # Check for immediate player blackjack
    if game.player_hand.value == 21:
        # Dealer plays to check for a push
        game.dealer_plays()
        result, multiplier = game.determine_winner()
        payout = int(game.bet_amount * multiplier)
        user_balances[user_id] += payout

        result_message = (
            f"🎉 <b>¡BLACKJACK!</b> 🎉\n\n"
            f"<b>Tu mano (Valor: {game.player_hand.value})</b>\n"
            f"{game.player_hand}\n\n"
            f"<b>Mano del crupier (Valor: {game.dealer_hand.value})</b>\n"
            f"{game.dealer_hand}\n\n"
        )

        if payout > 0:
            result_message += f"¡Ganaste {payout}! 🤑 Tu nuevo saldo es 💰 {user_balances[user_id]}."
        else: # Push
            result_message += f"¡Es un empate! Se te devuelve la apuesta. Tu saldo es 💰 {user_balances[user_id]}."

        await update.message.reply_text(result_message, parse_mode='HTML')
        del active_blackjack_games[user_id] # End game
    else:
        keyboard = [
            [
                InlineKeyboardButton("Pedir", callback_data='bj_hit'),
                InlineKeyboardButton("Plantarse", callback_data='bj_stand')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            f"♠️ ¡Partida de Blackjack iniciada con una apuesta de {bet_amount}! ♥️\n\n"
            f"<b>Tu mano (Valor: {game.player_hand.value})</b>\n"
            f"{game.player_hand}\n\n"
            f"<b>El crupier muestra</b>\n"
            f"{game.dealer_hand.cards[0][0]}{game.dealer_hand.cards[0][1]} ❔\n\n" #Mensaje mano del crupier
            "¿Cuál es tu jugada?"
        )
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all button presses from inline keyboards."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    data = query.data
    user_id = query.from_user.id

    # --- Menu Routing ---
    if data == 'menu_main':
        keyboard = [
            [InlineKeyboardButton("Roulette 🎡", callback_data='menu_roulette')],
            [InlineKeyboardButton("Blackjack ♠️", callback_data='menu_blackjack')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="¡Bienvenido al Casino! Elige un juego para jugar:",
            reply_markup=reply_markup # Traducir los mensajes del menú
        )
        return

    if data == 'menu_roulette':
        keyboard = [[InlineKeyboardButton("Volver ⏪", callback_data='menu_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="<b>Ruleta</b> 🎡\n\nUsa el comando <code>/roulette &lt;cantidad&gt; &lt;tipo&gt;</code> para jugar.\nEjemplo: <code>/roulette 10 rojo</code>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    if data == 'menu_blackjack':
        keyboard = [[InlineKeyboardButton("Volver ⏪", callback_data='menu_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="<b>Blackjack</b> ♠️\n\nUsa el comando <code>/blackjack &lt;cantidad&gt;</code> para iniciar una partida.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return

    # --- Blackjack Game Logic ---
    if user_id not in active_blackjack_games:
        await query.edit_message_text("Esta partida ha expirado o no se ha encontrado. Por favor, inicia una nueva.")
        return

    game = active_blackjack_games[user_id]

    if data == 'bj_hit':
        busted = game.player_hits()
        if busted:
            user_balances[user_id] -= game.bet_amount
            message = (
                f"Tu mano final:\n\n"
                f"<b>Tu mano (Valor: {game.player_hand.value})</b>\n"
                f"{game.player_hand}\n\n"
                f"💥 ¡TE PASASTE! 💥 Has perdido {game.bet_amount}. ¡Mejor suerte la próxima vez!\n"
                f"Tu nuevo saldo es: 💰 {user_balances[user_id]}"
            )
            await query.edit_message_text(text=message, parse_mode='HTML', reply_markup=None)
            del active_blackjack_games[user_id]
        else:
            keyboard = [[InlineKeyboardButton("Pedir", callback_data='bj_hit'), InlineKeyboardButton("Plantarse", callback_data='bj_stand')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = (
                f"¡Has pedido carta! Aquí está tu nueva mano:\n\n"
                f"<b>Tu mano (Valor: {game.player_hand.value})</b>\n"
                f"{game.player_hand}\n\n"
                "¿Te sientes con suerte?"
            )
            await query.edit_message_text(text=message, parse_mode='HTML', reply_markup=reply_markup)

    elif data == 'bj_stand':
        game.dealer_plays()
        result_text, multiplier = game.determine_winner()
        payout = int(game.bet_amount * multiplier)
        user_balances[user_id] += payout

        message = (
            f"Te plantas con {game.player_hand.value}. El crupier revela su mano...\n\n"
            f"<b>Tu mano (Valor: {game.player_hand.value})</b>\n"
            f"{game.player_hand}\n\n"
            f"<b>Mano del crupier (Valor: {game.dealer_hand.value})</b>\n"
            f"{game.dealer_hand}\n\n"
        )

        if result_text == "blackjack" or result_text == "win":
            message += f"¡GANAS {payout}! 🎉 Tu nuevo saldo es 💰 {user_balances[user_id]}."
        elif result_text == "loss" or result_text == "bust":
            message += f"HAS PERDIDO {abs(payout)}. 😔 Tu nuevo saldo es 💰 {user_balances[user_id]}."
        else:  # Push
            message += f"Es un EMPATE. Se te devuelve la apuesta. Tu saldo es 💰 {user_balances[user_id]}."

        await query.edit_message_text(text=message, parse_mode='HTML', reply_markup=None)
        del active_blackjack_games[user_id]

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and attempt to send a user-facing message."""
    print(f"Update {update} caused error {context.error}")

    # Try to find a chat_id to reply to, making the handler more robust
    chat_id = None
    if isinstance(update, Update) and update.effective_chat:
        chat_id = update.effective_chat.id

    if chat_id:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Ha ocurrido un error al procesar tu solicitud. Por favor, inténtalo de nuevo o usa /help."
            )
        except Exception as e:
            print(f"Failed to send error message to chat {chat_id}: {e}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("games", games_menu))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("roulette", roulette))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("blackjack", blackjack_start))
    application.add_handler(CallbackQueryHandler(button_handler))


    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()