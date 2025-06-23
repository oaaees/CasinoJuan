import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import your roulette logic
from roulette import spin_wheel, determine_outcome, ROULETTE_NUMBERS
# from player_data import get_player_balance, update_player_balance, store_bet, get_current_bet

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
if TOKEN is None:
    print("Error: TELEGRAM_TOKEN not found.")
    exit(1)

# In-memory store for player balances and current bets (for simplicity, replace with DB)
user_balances = {}
active_bets = {} # {user_id: {'amount': 10, 'type': 'red'}}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 1000 # Give new users a starting balance
    await update.message.reply_text(f"Welcome! Your balance is {user_balances[user_id]}. Use /help.")

async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /bet <amount> <type> (e.g., /bet 10 red)")
        return

    try:
        amount = int(context.args[0])
        bet_type = context.args[1].lower()
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if amount <= 0:
        await update.message.reply_text("Bet amount must be positive.")
        return
    if user_id not in user_balances or user_balances[user_id] < amount:
        await update.message.reply_text(f"Not enough balance! Your balance: {user_balances[user_id]}")
        return

    # Basic validation for bet type (expand this significantly!)
    valid_bet_types = list(ROULETTE_NUMBERS.values()) + [str(i) for i in range(37)] + ["odd", "even", "high", "low"] # etc.
    if bet_type not in valid_bet_types:
        await update.message.reply_text(f"Invalid bet type: '{bet_type}'. Valid types are numbers 0-36, red, black, green, etc.")
        return

    active_bets[user_id] = {'amount': amount, 'type': bet_type}
    await update.message.reply_text(f"Bet of {amount} on {bet_type} placed. Use /spin to play!")


async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in active_bets:
        await update.message.reply_text("You need to place a bet first! Use /bet <amount> <type>.")
        return

    bet_info = active_bets.pop(user_id) # Get and remove the bet
    bet_amount = bet_info['amount']
    bet_type = bet_info['type']

    winning_number = spin_wheel()
    winning_color = ROULETTE_NUMBERS[winning_number]
    outcome = determine_outcome(winning_number, bet_amount, bet_type)

    user_balances[user_id] += outcome # Update balance

    if outcome > 0:
        message = f"The ball landed on {winning_number} ({winning_color})! You WON {outcome}! Your new balance: {user_balances[user_id]}."
    else:
        message = f"The ball landed on {winning_number} ({winning_color}). You lost {abs(outcome)}. Your new balance: {user_balances[user_id]}."

    await update.message.reply_text(message)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_balance = user_balances.get(user_id, 0) # Get balance or 0 if not set
    await update.message.reply_text(f"Your current balance is: {current_balance}")


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bet", bet))
    application.add_handler(CommandHandler("spin", spin))
    application.add_handler(CommandHandler("balance", balance))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()