import random

ROULETTE_NUMBERS = {
    0: "green",
    1: "red", 2: "black", 3: "red", 4: "black", 5: "red", 6: "black",
    7: "red", 8: "black", 9: "red", 10: "black", 11: "black", 12: "red",
    13: "black", 14: "red", 15: "black", 16: "red", 17: "black", 18: "red",
    19: "red", 20: "black", 21: "red", 22: "black", 23: "red", 24: "black",
    25: "red", 26: "black", 27: "red", 28: "black", 29: "black", 30: "red",
    31: "black", 32: "red", 33: "black", 34: "red", 35: "black", 36: "red"
}

def spin_wheel():
    """Simulates a roulette spin and returns the winning number."""
    return random.randint(0, 36)

def determine_outcome(winning_number: int, bet_amount: int, bet_type: str) -> int:
    """Calculates win/loss based on winning number and bet type."""
    bet_type = bet_type.lower()

    # Payouts are for winnings (e.g., 1:1 payout means you win 1 * bet_amount)
    if bet_type in ["red", "black"] and ROULETTE_NUMBERS[winning_number] == bet_type:
        return bet_amount * 1  # 1:1 payout

    if bet_type == "green" and winning_number == 0:
        return bet_amount * 35  # Same as a single number bet

    if bet_type.isdigit() and int(bet_type) == winning_number:
        return bet_amount * 35  # 35:1 payout

    if bet_type == "odd" and winning_number != 0 and winning_number % 2 != 0:
        return bet_amount * 1  # 1:1 payout
    if bet_type == "even" and winning_number != 0 and winning_number % 2 == 0:
        return bet_amount * 1  # 1:1 payout
    if bet_type == "high" and 19 <= winning_number <= 36:
        return bet_amount * 1  # 1:1 payout
    if bet_type == "low" and 1 <= winning_number <= 18:
        return bet_amount * 1  # 1:1 payout
    if bet_type == "1st12" and 1 <= winning_number <= 12:
        return bet_amount * 2  # 2:1 payout
    if bet_type == "2nd12" and 13 <= winning_number <= 24:
        return bet_amount * 2  # 2:1 payout
    if bet_type == "3rd12" and 25 <= winning_number <= 36:
        return bet_amount * 2  # 2:1 payout
    if bet_type == "col1" and winning_number != 0 and winning_number % 3 == 1:
        return bet_amount * 2  # 2:1 payout
    if bet_type == "col2" and winning_number != 0 and winning_number % 3 == 2:
        return bet_amount * 2  # 2:1 payout
    if bet_type == "col3" and winning_number != 0 and winning_number % 3 == 0:
        return bet_amount * 2  # 2:1 payout

    # If none of the above winning conditions were met, the player loses.
    return -bet_amount