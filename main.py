import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import your roulette logic
from roulette import spin_wheel, determine_outcome, ROULETTE_NUMBERS

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
if TOKEN is None:
    print("Error: TELEGRAM_TOKEN not found in environment variables or .env file.")
    exit(1)

# In-memory stores for player data (for simplicity, consider a database for persistence)
user_balances = {}       # {user_id: balance}
# This dictionary now stores the current/last bet for each user.
# It is updated by /bet and read by /spin. It is NOT popped after spin.
active_bets = {}         # {user_id: {'amount': 10, 'type': 'red'}}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 1000 # Give new users a starting balance
    await update.message.reply_text(f"Welcome! Your balance is {user_balances[user_id]}. Use /help for commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text("Here are the commands:\n"
                                    "/start - Start the bot\n"
                                    "/bet <amount> <type> - Place a new bet (e.g., /bet 10 red)\n"
                                    "/spin - Spin the wheel (uses current or last bet)\n"
                                    "/balance - Check your current balance")


async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /bet <amount> <type> (e.g., /bet 10 red, /bet 5 17)")
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
        await update.message.reply_text(f"Not enough balance! Your balance: {user_balances.get(user_id, 0)}")
        return

    # Basic validation for bet type (expand this significantly!)
    unique_colors = list(set(ROULETTE_NUMBERS.values()))
    valid_number_bets = [str(i) for i in range(37)]
    common_bet_types = ["odd", "even", "high", "low", "1st12", "2nd12", "3rd12", "col1", "col2", "col3"]
    valid_bet_types = unique_colors + valid_number_bets + common_bet_types

    if bet_type not in valid_bet_types:
        await update.message.reply_text(f"Invalid bet type: '{bet_type}'. Please use a number (0-36), a color (red/black/green), or common types like odd/even/high/low/1st12/etc.")
        return

    # Store the new bet in active_bets. This automatically becomes the 'last_bet'
    # for subsequent spins until a new /bet command is used.
    active_bets[user_id] = {'amount': amount, 'type': bet_type}
    await update.message.reply_text(f"Bet of {amount} on {bet_type} placed. Use /spin to play!")


async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if there's any active/last bet for the user
    if user_id not in active_bets:
        await update.message.reply_text("You need to place a bet first! Use /bet <amount> <type>.")
        return

    bet_info = active_bets[user_id] # Retrieve the last stored bet
    bet_amount = bet_info['amount']
    bet_type = bet_info['type']

    # Important: Check if the user can still afford the last bet
    if user_id not in user_balances or user_balances[user_id] < bet_amount:
        await update.message.reply_text(f"Cannot spin with your last bet ({bet_amount} on {bet_type})! You don't have enough balance ({user_balances.get(user_id, 0)}). Please place a new bet.")
        # Optionally, clear the invalid last bet
        if user_id in active_bets:
            del active_bets[user_id]
        return

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
    current_balance = user_balances.get(user_id, 0)
    await update.message.reply_text(f"Your current balance is: {current_balance}")

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
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("bet", bet))
    application.add_handler(CommandHandler("spin", spin))
    application.add_handler(CommandHandler("balance", balance))

    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()