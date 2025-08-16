import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Import your roulette logic
from roulette import spin_wheel, determine_outcome, ROULETTE_NUMBERS
from blackjack import BlackjackGame

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
        "Welcome to the Casino! Choose a game to play:", reply_markup=reply_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 1000 # Give new users a starting balance
        await update.message.reply_text(f"Welcome! I've created an account for you with a starting balance of 1000.")
    
    await games_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    help_text = (
        "<b>--- General Commands ---</b>\n"
        "/start - Initialize your account\n"
        "/games - Show the main game menu\n"
        "/balance - Check your current balance\n"
        "\n<b>--- Roulette ---</b>\n"
        "/roulette &lt;amount&gt; &lt;type&gt; - Place a bet and spin the wheel (e.g., <code>/roulette 10 red</code>)\n"
        "\n<b>--- Blackjack ---</b>\n"
        "/blackjack &lt;amount&gt; - Start a new game of Blackjack\n\n"
        "During a Blackjack game, use the <b>Hit</b> and <b>Stand</b> buttons instead of commands."
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Places a bet and immediately spins the roulette wheel."""
    user_id = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /roulette <amount> <type> (e.g., /roulette 10 red)")
        return

    try:
        bet_amount = int(context.args[0])
        bet_type = context.args[1].lower()
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if bet_amount <= 0:
        await update.message.reply_text("Bet amount must be positive.")
        return
    if user_id not in user_balances or user_balances[user_id] < bet_amount:
        await update.message.reply_text(f"Not enough balance! Your balance: {user_balances.get(user_id, 0)}")
        return

    # Validate bet type
    unique_colors = list(set(ROULETTE_NUMBERS.values()))
    valid_number_bets = [str(i) for i in range(37)]
    common_bet_types = ["odd", "even", "high", "low", "1st12", "2nd12", "3rd12", "col1", "col2", "col3"]
    valid_bet_types = unique_colors + valid_number_bets + common_bet_types

    if bet_type not in valid_bet_types:
        await update.message.reply_text(f"Invalid bet type: '{bet_type}'. Please use a number (0-36), a color, or common types like odd/even/high/low/1st12/col1.")
        return

    # Perform the spin immediately
    winning_number = spin_wheel()
    winning_color = ROULETTE_NUMBERS[winning_number]
    color_emoji = "🟢" if winning_color == "green" else ("🔴" if winning_color == "red" else "⚫")

    outcome = determine_outcome(winning_number, bet_amount, bet_type)
    user_balances[user_id] += outcome

    if outcome > 0:
        message = (
            f"Spinning the wheel... 🎡\n"
            f"The ball landed on: {color_emoji} {winning_number}!\n\n"
            f"🎉 Congratulations! You WON {outcome}! 🎉\n"
            f"Your new balance: 💰 {user_balances[user_id]}"
        )
    else:
        message = (
            f"Spinning the wheel... 🎡\n"
            f"The ball landed on: {color_emoji} {winning_number}.\n\n"
            f"Better luck next time! You lost {abs(outcome)}. 😔\n"
            f"Your new balance: 💰 {user_balances[user_id]}"
        )

    await update.message.reply_text(message)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_balance = user_balances.get(user_id, 0)
    await update.message.reply_text(f"Your current balance is: {current_balance}")


async def blackjack_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts a new game of blackjack."""
    user_id = update.effective_user.id

    if user_id in active_blackjack_games:
        await update.message.reply_text("You already have a game in progress! Please finish it before starting a new one.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /blackjack <amount>")
        return

    try:
        bet_amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if bet_amount <= 0:
        await update.message.reply_text("Bet amount must be positive.")
        return

    if user_id not in user_balances or user_balances[user_id] < bet_amount:
        await update.message.reply_text(f"Not enough balance! Your balance: {user_balances.get(user_id, 0)}")
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
            f"🎉 <b>BLACKJACK!</b> 🎉\n\n"
            f"<b>Your Hand (Value: {game.player_hand.value})</b>\n"
            f"{game.player_hand}\n\n"
            f"<b>Dealer's Hand (Value: {game.dealer_hand.value})</b>\n"
            f"{game.dealer_hand}\n\n"
        )

        if payout > 0:
            result_message += f"You win {payout}! 🤑 Your new balance is 💰 {user_balances[user_id]}."
        else: # Push
            result_message += f"It's a push! Your bet is returned. Your balance is 💰 {user_balances[user_id]}."

        await update.message.reply_text(result_message, parse_mode='HTML')
        del active_blackjack_games[user_id] # End game
    else:
        keyboard = [
            [
                InlineKeyboardButton("Hit", callback_data='bj_hit'),
                InlineKeyboardButton("Stand", callback_data='bj_stand')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            f"♠️ Blackjack game started with a bet of {bet_amount}! ♥️\n\n"
            f"<b>Your Hand (Value: {game.player_hand.value})</b>\n"
            f"{game.player_hand}\n\n"
            f"<b>Dealer's Showing</b>\n"
            f"{game.dealer_hand.cards[0][0]}{game.dealer_hand.cards[0][1]} ❔\n\n"
            "What's your move?"
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
            text="Welcome to the Casino! Choose a game to play:",
            reply_markup=reply_markup
        )
        return

    if data == 'menu_roulette':
        keyboard = [[InlineKeyboardButton("Back ⏪", callback_data='menu_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="<b>Roulette</b> 🎡\n\nUse the command <code>/roulette &lt;amount&gt; &lt;type&gt;</code> to play.\nExample: <code>/roulette 10 red</code>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    if data == 'menu_blackjack':
        keyboard = [[InlineKeyboardButton("Back ⏪", callback_data='menu_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="<b>Blackjack</b> ♠️\n\nUse the command <code>/blackjack &lt;amount&gt;</code> to start a game.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return

    # --- Blackjack Game Logic ---
    if user_id not in active_blackjack_games:
        await query.edit_message_text("This game has expired or was not found. Please start a new one.")
        return

    game = active_blackjack_games[user_id]

    if data == 'bj_hit':
        busted = game.player_hits()
        if busted:
            user_balances[user_id] -= game.bet_amount
            message = (
                f"Your final hand:\n\n"
                f"<b>Your Hand (Value: {game.player_hand.value})</b>\n"
                f"{game.player_hand}\n\n"
                f"💥 BUST! 💥 You lost {game.bet_amount}. Better luck next time!\n"
                f"Your new balance: 💰 {user_balances[user_id]}"
            )
            await query.edit_message_text(text=message, parse_mode='HTML', reply_markup=None)
            del active_blackjack_games[user_id]
        else:
            keyboard = [[InlineKeyboardButton("Hit", callback_data='bj_hit'), InlineKeyboardButton("Stand", callback_data='bj_stand')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = (
                f"You hit! Here's your new hand:\n\n"
                f"<b>Your Hand (Value: {game.player_hand.value})</b>\n"
                f"{game.player_hand}\n\n"
                "Feeling lucky?"
            )
            await query.edit_message_text(text=message, parse_mode='HTML', reply_markup=reply_markup)

    elif data == 'bj_stand':
        game.dealer_plays()
        result_text, multiplier = game.determine_winner()
        payout = int(game.bet_amount * multiplier)
        user_balances[user_id] += payout

        message = (
            f"You stand with {game.player_hand.value}. The dealer reveals their hand...\n\n"
            f"<b>Your Hand (Value: {game.player_hand.value})</b>\n"
            f"{game.player_hand}\n\n"
            f"<b>Dealer's Hand (Value: {game.dealer_hand.value})</b>\n"
            f"{game.dealer_hand}\n\n"
        )

        if result_text == "blackjack" or result_text == "win":
            message += f"You WIN {payout}! 🎉 Your new balance is 💰 {user_balances[user_id]}."
        elif result_text == "loss" or result_text == "bust":
            message += f"You LOST {abs(payout)}. 😔 Your new balance is 💰 {user_balances[user_id]}."
        else:  # Push
            message += f"It's a PUSH. Your bet is returned. Your balance is 💰 {user_balances[user_id]}."

        await query.edit_message_text(text=message, parse_mode='HTML', reply_markup=None)
        del active_blackjack_games[user_id]

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred while processing your request. Please try again or use /help."
        )

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