import os
from dotenv import load_dotenv
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Import your roulette logic
from roulette import spin_wheel, determine_outcome, ROULETTE_NUMBERS
from blackjack import BlackjackGame
from poker import VideoPokerGame

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
active_poker_games = {}      # {user_id: VideoPokerGame_instance}

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with the main game menu."""
    keyboard = [
        [InlineKeyboardButton("Roulette 🎡", callback_data='menu_roulette')],
        [InlineKeyboardButton("Blackjack ♠️", callback_data='menu_blackjack')],
        [InlineKeyboardButton("Video Poker 🃏", callback_data='menu_poker')],
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
        "<b>/roulette</b> - Inicia una apuesta interactiva.\n"
        "<b>/roulette &lt;cantidad&gt; &lt;tipo&gt;</b> - Apuesta directamente (ej: <code>/roulette 10 rojo</code>).\n"
        "<b>Tipos de Apuesta:</b>\n"
        "  • <b>Número:</b> Un número del 0 al 36 (ej: <code>17</code>)\n"
        "  • <b>Colores:</b> <code>rojo</code>, <code>negro</code>\n"
        "  • <b>Pares/Impares:</b> <code>par</code>, <code>impar</code>\n"
        "  • <b>Altos/Bajos:</b> <code>alto</code> (19-36), <code>bajo</code> (1-18)\n"
        "  • <b>Docenas:</b> <code>1ra12</code> (1-12), <code>2da12</code> (13-24), <code>3ra12</code> (25-36)\n"
        "  • <b>Columnas:</b> <code>columna1</code>, <code>columna2</code>, <code>columna3</code>\n\n"
        "<b>--- Blackjack ---</b>\n\n"
        "<b>/blackjack</b> - Inicia una apuesta interactiva de Blackjack.\n"
        "<b>/blackjack &lt;cantidad&gt;</b> - Comienza un juego con una apuesta específica.\n\n"
        "<b>--- Video Poker ---</b>\n\n"
        "<b>/poker</b> - Inicia una apuesta interactiva de Video Poker.\n"
        "<b>/poker &lt;cantidad&gt;</b> - Comienza un juego con una apuesta específica.\n\n"
        "Durante una partida de Blackjack o Poker, usa los botones en lugar de los comandos."
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


async def _execute_roulette_spin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet_amount: int, bet_type: str, is_callback: bool):
    """
    Handles the core logic of a roulette spin and sends the result message.
    Can be called from a command or a callback query.
    """
    # Check balance
    if user_id not in user_balances or user_balances[user_id] < bet_amount:
        message_text = f"¡No tienes saldo suficiente! Tu saldo es: {user_balances.get(user_id, 0)}"
        if is_callback:
            await update.callback_query.edit_message_text(message_text, reply_markup=None)
        else:
            await update.message.reply_text(message_text)
        return

    # Perform the spin
    winning_number = spin_wheel()
    winning_color = ROULETTE_NUMBERS[winning_number]
    color_emoji = "🟢" if winning_color == "green" else ("🔴" if winning_color == "red" else "⚫")

    outcome = determine_outcome(winning_number, bet_amount, bet_type)
    user_balances[user_id] += outcome
    new_balance = user_balances[user_id]

    base_message = (
        f"Girando la ruleta... 🎡\n"
        f"La bola ha caído en: {color_emoji} {winning_number}!\n\n"
    )

    if outcome > 0:
        win_messages = [
            f"🎉 ¡Cha-ching! ¡GANASTE {outcome}! Tu billetera ahora está más gorda: 💰 {new_balance}",
            f"¡SÍ! ¡La ruleta te favorece! Unos geniales {outcome} créditos son tuyos. Nuevo balance: 💰 {new_balance}",
            f"🥳 ¡Ganador, ganador, cena de pollo! ¡Has ganado {outcome}! Balance total: 💰 {new_balance}",
        ]
        message = base_message + random.choice(win_messages)
    else:
        loss_messages = [
            f"Vaya. La casa gana esta vez. Has perdido {abs(outcome)}. Tu saldo ahora es: 💰 {new_balance}",
            f"¡Casi! La suerte no está de tu lado. Has perdido {abs(outcome)}. Saldo restante: 💰 {new_balance}",
            f"Esta vez no pudo ser. La ruleta no giró a tu favor. Has perdido {abs(outcome)}. Te quedan 💰 {new_balance}.",
        ]
        message = base_message + f"😔 {random.choice(loss_messages)}"

    if is_callback:
        await update.callback_query.edit_message_text(text=message, reply_markup=None)
    else:
        await update.message.reply_text(message)


async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Realiza una apuesta en la ruleta, ya sea por comando o interactivamente."""
    user_id = update.effective_user.id

    # Case 1: /roulette -> Show interactive bet type selection
    if len(context.args) == 0:
        keyboard = [
            [
                InlineKeyboardButton("Rojo 🔴", callback_data='roulette_type_red'),
                InlineKeyboardButton("Negro ⚫", callback_data='roulette_type_black'),
            ],
            [
                InlineKeyboardButton("Par", callback_data='roulette_type_even'),
                InlineKeyboardButton("Impar", callback_data='roulette_type_odd'),
            ],
            [
                InlineKeyboardButton("Bajo (1-18)", callback_data='roulette_type_low'),
                InlineKeyboardButton("Alto (19-36)", callback_data='roulette_type_high'),
            ],
            [
                InlineKeyboardButton("Más Opciones ➡️", callback_data='roulette_more')
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🎡 Ruleta: Elige tu tipo de apuesta:",
            reply_markup=reply_markup
        )
        return

    # Case 2: /roulette <amount> <type> -> Direct play
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /roulette <cantidad> <tipo> o simplemente /roulette para elegir de una lista.")
        return

    try:
        bet_type_translations = {
            "rojo": "red", "negro": "black", "verde": "green",
            "par": "even", "impar": "odd",
            "alto": "high", "bajo": "low",
            "1ra12": "1st12", "2da12": "2nd12", "3ra12": "3rd12",
            "columna1": "col1", "columna2": "col2", "columna3": "col3",
        }
        bet_amount = int(context.args[0])
        raw_bet_type = " ".join(context.args[1:]).lower()
        bet_type = bet_type_translations.get(raw_bet_type, raw_bet_type) # Translate if found
    except ValueError:
        await update.message.reply_text("Cantidad inválida. Por favor, introduce un número.")
        return #Mensaje de cantidad invalida

    if bet_amount <= 0:
        await update.message.reply_text("La cantidad de la apuesta debe ser positiva.")
        return
    if bet_type not in VALID_ROULETTE_BETS:
        await update.message.reply_text(
            f"Tipo de apuesta inválido: '{raw_bet_type}'.\n"
            "Por favor, usa un número (0-36), un color (rojo/negro/verde), "
            "o tipos comunes (par/impar, alto/bajo, 1ra12, columna1, etc.)."
        )
        return

    # Call the helper to execute the spin
    await _execute_roulette_spin(update, context, user_id, bet_amount, bet_type, is_callback=False)

async def poker_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts a new game of Video Poker."""
    user_id = update.effective_user.id

    if user_id in active_poker_games:
        await update.message.reply_text("Ya tienes un juego de Video Poker en progreso. ¡Termínalo primero!")
        return

    # Case 1: /poker (no arguments) -> Show bet buttons
    if len(context.args) == 0:
        keyboard = [
            [
                InlineKeyboardButton("10", callback_data='poker_bet_10'),
                InlineKeyboardButton("50", callback_data='poker_bet_50')
            ],
            [
                InlineKeyboardButton("100", callback_data='poker_bet_100'),
                InlineKeyboardButton("250", callback_data='poker_bet_250')
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Elige tu apuesta para Video Poker:",
            reply_markup=reply_markup
        )
        return

    # Case 2: /poker <amount>
    if len(context.args) == 1:
        try:
            bet_amount = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Cantidad inválida. Por favor, introduce un número.")
            return

        if bet_amount <= 0:
            await update.message.reply_text("La cantidad de la apuesta debe ser positiva.")
            return

        if user_id not in user_balances or user_balances[user_id] < bet_amount:
            await update.message.reply_text(f"¡No tienes saldo suficiente! Tu saldo es: {user_balances.get(user_id, 0)}")
            return
    else: # Case 3: Invalid arguments
        await update.message.reply_text("Uso: /poker <cantidad> o simplemente /poker para elegir de una lista.")
        return

    # Start the game and send the first message
    await _start_poker_game(update, context, user_id, bet_amount, is_callback=False)

async def _start_poker_game(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet_amount: int, is_callback: bool):
    """Helper function to create and start a poker game, sending the initial message."""
    game = VideoPokerGame(bet_amount)
    game.start_game()
    active_poker_games[user_id] = game

    keyboard = _build_poker_keyboard(game)
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = (
        f"🃏 ¡Video Poker! Apuesta: {bet_amount}\n\n"
        f"<b>Tu mano:</b> {game.get_hand_str()}\n\n"
        "Selecciona las cartas que quieres conservar y luego pulsa 'Robar'."
    )

    if is_callback:
        await update.callback_query.edit_message_text(text=message_text, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=message_text, parse_mode='HTML', reply_markup=reply_markup)

def _build_poker_keyboard(game: VideoPokerGame) -> list:
    """Builds the dynamic keyboard for the poker game, showing hold status."""
    hold_buttons = [InlineKeyboardButton(f"{'✅ ' if game.held_indices[i] else ''}{card[0]}{card[1]}", callback_data=f'poker_hold_{i}') for i, card in enumerate(game.hand)]
    keyboard = [hold_buttons, [InlineKeyboardButton("Robar Cartas ➡️", callback_data='poker_draw')]]
    return keyboard

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

    # Case 1: /blackjack (no arguments) -> Show bet buttons
    if len(context.args) == 0:
        keyboard = [
            [
                InlineKeyboardButton("10", callback_data='bj_bet_10'),
                InlineKeyboardButton("50", callback_data='bj_bet_50')
            ],
            [
                InlineKeyboardButton("100", callback_data='bj_bet_100'),
                InlineKeyboardButton("250", callback_data='bj_bet_250')
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Elige tu apuesta para el Blackjack:",
            reply_markup=reply_markup
        )
        return

    # Case 2: /blackjack <amount>
    if len(context.args) == 1:
        try:
            bet_amount = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Cantidad inválida. Por favor, introduce un número.")
            return

        if bet_amount <= 0:
            await update.message.reply_text("La cantidad de la apuesta debe ser positiva.")
            return

        if user_id not in user_balances or user_balances[user_id] < bet_amount:
            await update.message.reply_text(f"¡No tienes saldo suficiente! Tu saldo es: {user_balances.get(user_id, 0)}")
            return
    else: # Case 3: Invalid arguments
        await update.message.reply_text("Uso: /blackjack <cantidad> o simplemente /blackjack para elegir de una lista.")
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
            [InlineKeyboardButton("Video Poker 🃏", callback_data='menu_poker')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="¡Bienvenido al Casino! Elige un juego para jugar:",
            reply_markup=reply_markup # Traducir los mensajes del menú
        )
        return

    if data == 'menu_roulette':
        keyboard = [
            [
                InlineKeyboardButton("Rojo 🔴", callback_data='roulette_type_red'),
                InlineKeyboardButton("Negro ⚫", callback_data='roulette_type_black'),
            ],
            [
                InlineKeyboardButton("Par", callback_data='roulette_type_even'),
                InlineKeyboardButton("Impar", callback_data='roulette_type_odd'),
            ],
            [
                InlineKeyboardButton("Bajo (1-18)", callback_data='roulette_type_low'),
                InlineKeyboardButton("Alto (19-36)", callback_data='roulette_type_high'),
            ],
            [
                InlineKeyboardButton("Más Opciones ➡️", callback_data='roulette_more')
            ],
            [InlineKeyboardButton("Volver al Menú Principal ⏪", callback_data='menu_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="🎡 Ruleta: Elige tu tipo de apuesta:",
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
    if data == 'menu_poker':
        keyboard = [
            [
                InlineKeyboardButton("10", callback_data='poker_bet_10'),
                InlineKeyboardButton("50", callback_data='poker_bet_50')
            ],
            [
                InlineKeyboardButton("100", callback_data='poker_bet_100'),
                InlineKeyboardButton("250", callback_data='poker_bet_250')
            ],
            [InlineKeyboardButton("Volver al Menú Principal ⏪", callback_data='menu_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Elige tu apuesta para Video Poker:", reply_markup=reply_markup)
        return

    if data == 'roulette_more':
        keyboard = [
            [
                InlineKeyboardButton("1ra Docena (1-12)", callback_data='roulette_type_1st12'),
                InlineKeyboardButton("1ra Columna", callback_data='roulette_type_col1'),
            ],
            [
                InlineKeyboardButton("2da Docena (13-24)", callback_data='roulette_type_2nd12'),
                InlineKeyboardButton("2da Columna", callback_data='roulette_type_col2'),
            ],
            [
                InlineKeyboardButton("3ra Docena (25-36)", callback_data='roulette_type_3rd12'),
                InlineKeyboardButton("3ra Columna", callback_data='roulette_type_col3'),
            ],
            [InlineKeyboardButton("⏪ Volver", callback_data='menu_roulette')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="🎡 Ruleta: Apuestas por Docenas y Columnas:",
            reply_markup=reply_markup
        )
        return

    # --- Roulette Bet Selection ---
    if data.startswith('roulette_type_'):
        bet_type = data.split('_')[2]

        # Map callback data to user-friendly text and canonical bet type
        bet_type_map = {
            'red': ('Rojo 🔴', 'red'),
            'black': ('Negro ⚫', 'black'),
            'even': ('Par', 'even'),
            'odd': ('Impar', 'odd'),
            'low': ('Bajo (1-18)', 'low'),
            'high': ('Alto (19-36)', 'high'),
            '1st12': ('1ra Docena (1-12)', '1st12'),
            '2nd12': ('2da Docena (13-24)', '2nd12'),
            '3rd12': ('3ra Docena (25-36)', '3rd12'),
            'col1': ('1ra Columna', 'col1'),
            'col2': ('2da Columna', 'col2'),
            'col3': ('3ra Columna', 'col3'),
        }

        display_text, canonical_type = bet_type_map.get(bet_type, ("Desconocido", None))

        if not canonical_type:
            await query.edit_message_text("Error: Tipo de apuesta no reconocido.")
            return

        keyboard = [
            [
                InlineKeyboardButton("10", callback_data=f'roulette_play_{canonical_type}_10'),
                InlineKeyboardButton("50", callback_data=f'roulette_play_{canonical_type}_50')
            ],
            [
                InlineKeyboardButton("100", callback_data=f'roulette_play_{canonical_type}_100'),
                InlineKeyboardButton("250", callback_data=f'roulette_play_{canonical_type}_250')
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Apuesta: {display_text}\n\nElige la cantidad a apostar:",
            reply_markup=reply_markup
        )
        return

    if data.startswith('roulette_play_'):
        parts = data.split('_')
        try:
            bet_type = parts[2]
            bet_amount = int(parts[3])
        except (IndexError, ValueError):
            await query.edit_message_text("Error al procesar la apuesta. Inténtalo de nuevo.")
            return

        await _execute_roulette_spin(update, context, user_id, bet_amount, bet_type, is_callback=True)
        return

    # --- Video Poker Bet Selection ---
    if data.startswith('poker_bet_'):
        if user_id in active_poker_games:
            await query.answer("Ya tienes un juego de Video Poker en progreso. ¡Termínalo primero!", show_alert=True)
            return

        try:
            bet_amount = int(data.split('_')[2])
        except (ValueError, IndexError):
            await query.edit_message_text("Error al procesar la apuesta. Por favor, inténtalo de nuevo.")
            return

        if user_id not in user_balances or user_balances[user_id] < bet_amount:
            await query.edit_message_text(f"¡No tienes saldo suficiente! Tu saldo es: {user_balances.get(user_id, 0)}")
            return

        await _start_poker_game(update, context, user_id, bet_amount, is_callback=True)
        return

    # --- Video Poker Game Logic ---
    if data.startswith('poker_hold_'):
        if user_id not in active_poker_games:
            await query.edit_message_text("Esta partida ha expirado. Por favor, inicia una nueva.")
            return
        game = active_poker_games[user_id]
        card_index = int(data.split('_')[2])
        game.toggle_hold(card_index)

        keyboard = _build_poker_keyboard(game)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        return

    if data == 'poker_draw':
        if user_id not in active_poker_games:
            await query.edit_message_text("Esta partida ha expirado. Por favor, inicia una nueva.")
            return
        game = active_poker_games[user_id]
        game.draw()
        hand_name, payout = game.evaluate_hand()
        user_balances[user_id] += payout

        result_message = (
            f"Robando cartas...\n\n"
            f"<b>Mano Final:</b> {game.get_hand_str()}\n"
            f"<b>Resultado:</b> {hand_name}!\n\n"
        )
        if payout > 0:
            result_message += f"¡Felicidades! ¡Ganaste {payout}! 🤑\nTu nuevo saldo es 💰 {user_balances[user_id]}."
        else:
            result_message += f"No hubo suerte esta vez. Perdiste {abs(payout)}. 😔\nTu saldo es 💰 {user_balances[user_id]}."

        await query.edit_message_text(text=result_message, parse_mode='HTML', reply_markup=None)
        del active_poker_games[user_id]
        return

    # --- Blackjack Bet Selection ---
    if data.startswith('bj_bet_'):
        if user_id in active_blackjack_games:
            await query.answer("Ya tienes un juego en progreso. ¡Termínalo primero!", show_alert=True)
            return

        try:
            bet_amount = int(data.split('_')[2])
        except (ValueError, IndexError):
            await query.edit_message_text("Error al procesar la apuesta. Por favor, inténtalo de nuevo.")
            return

        if user_id not in user_balances or user_balances[user_id] < bet_amount:
            await query.edit_message_text(f"¡No tienes saldo suficiente! Tu saldo es: {user_balances.get(user_id, 0)}")
            return

        # Create and store the game
        game = BlackjackGame(bet_amount)
        game.start_game()
        active_blackjack_games[user_id] = game

        # Check for immediate player blackjack
        if game.player_hand.value == 21:
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

            await query.edit_message_text(text=result_message, parse_mode='HTML', reply_markup=None)
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
                f"{game.dealer_hand.cards[0][0]}{game.dealer_hand.cards[0][1]} ❔\n\n"
                "¿Cuál es tu jugada?"
            )
            await query.edit_message_text(text=message, parse_mode='HTML', reply_markup=reply_markup)
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
                f"<b>El crupier muestra</b>\n"
                f"{game.dealer_hand.cards[0][0]}{game.dealer_hand.cards[0][1]} ❔\n\n"
                "¿Cuál es tu jugada?"
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
    application.add_handler(CommandHandler("poker", poker_start))
    application.add_handler(CallbackQueryHandler(button_handler))


    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()