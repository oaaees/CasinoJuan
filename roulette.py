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
    # ... your logic for calculating payouts ...
    payout = 0
    won = False

    if bet_type.lower() in ["red", "black", "green"]:
        if ROULETTE_NUMBERS[winning_number] == bet_type.lower():
            won = True
            payout = bet_amount * 1 # Simple example, adjust for 0/00
    elif bet_type.isdigit() and int(bet_type) == winning_number:
        won = True
        payout = bet_amount * 35

    return payout if won else -bet_amount

# Add more helper functions related to roulette here, e.g.:
def is_red(number):
    return ROULETTE_NUMBERS.get(number) == "red"

def is_black(number):
    return ROULETTE_NUMBERS.get(number) == "black"

# etc.