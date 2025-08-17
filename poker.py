from collections import Counter
from typing import List, Tuple

# Re-using the card logic from blackjack
from blackjack import Card, Deck, RANKS

# --- Payouts for Jacks or Better (Multiplier for the bet) ---
PAYOUT_TABLE = {
    "Royal Flush": 800,
    "Straight Flush": 50,
    "Four of a Kind": 25,
    "Full House": 9,
    "Flush": 6,
    "Straight": 4,
    "Three of a Kind": 3,
    "Two Pair": 2,
    "Jacks or Better": 1,
    "Nothing": -1,  # Represents a loss of the original bet
}


# --- Game State Class ---
class VideoPokerGame:
    """Manages the state of a single Jacks or Better video poker game."""
    def __init__(self, bet_amount: int):
        self.deck = Deck()
        self.hand: List[Card] = []
        self.held_indices = [False, False, False, False, False]
        self.bet_amount = bet_amount
        self.game_over = False

    def start_game(self):
        """Deals the initial 5 cards."""
        for _ in range(5):
            self.hand.append(self.deck.deal())

    def toggle_hold(self, index: int):
        """Toggles the hold status of a card at a given index."""
        if 0 <= index < 5:
            self.held_indices[index] = not self.held_indices[index]

    def draw(self):
        """Replaces un-held cards with new cards from the deck."""
        for i in range(5):
            if not self.held_indices[i]:
                self.hand[i] = self.deck.deal()
        self.game_over = True

    def evaluate_hand(self) -> Tuple[str, int]:
        """
        Evaluates the final hand and returns the hand name and the payout amount.
        """
        # Use RANKS.index to get a sortable value for each card rank
        sorted_ranks = sorted([RANKS.index(card[0]) for card in self.hand])
        suits = [card[1] for card in self.hand]

        is_flush = len(set(suits)) == 1
        # Check for standard straight (e.g., 5, 6, 7, 8, 9)
        is_straight = (len(set(sorted_ranks)) == 5) and (sorted_ranks[4] - sorted_ranks[0] == 4)
        # Check for Ace-low straight (A, 2, 3, 4, 5)
        if sorted_ranks == [0, 1, 2, 3, 12]: # Indices for 2, 3, 4, 5, A
            is_straight = True

        hand_name = "Nothing" # Default case

        if is_straight and is_flush:
            # Check for Royal Flush (10, J, Q, K, A)
            if sorted_ranks == [8, 9, 10, 11, 12]: # Indices for 10, J, Q, K, A
                hand_name = "Royal Flush"
            else:
                hand_name = "Straight Flush"
        elif is_flush:
            hand_name = "Flush"
        elif is_straight:
            hand_name = "Straight"
        else:
            # Check for pairs, three/four of a kind by counting ranks
            rank_counts = Counter(card[0] for card in self.hand)
            counts = sorted(rank_counts.values(), reverse=True)

            if counts[0] == 4:
                hand_name = "Four of a Kind"
            elif counts == [3, 2]:
                hand_name = "Full House"
            elif counts[0] == 3:
                hand_name = "Three of a Kind"
            elif counts == [2, 2, 1]:
                hand_name = "Two Pair"
            elif counts[0] == 2:
                # Find the rank of the pair to check if it's Jacks or better
                pair_rank_str = [rank for rank, count in rank_counts.items() if count == 2][0]
                if RANKS.index(pair_rank_str) >= 9:  # 9 is the index for 'J'
                    hand_name = "Jacks or Better"

        payout_multiplier = PAYOUT_TABLE.get(hand_name, -1)
        payout = int(self.bet_amount * payout_multiplier)
        return hand_name, payout

    def get_hand_str(self) -> str:
        """Returns a string representation of the hand."""
        return ' '.join([f"{card[0]}{card[1]}" for card in self.hand])