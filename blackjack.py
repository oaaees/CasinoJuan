import random
from typing import List, Tuple

# --- Constants ---
SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
VALUES = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}

Card = Tuple[str, str]  # (Rank, Suit)

# --- Deck Class ---
class Deck:
    """Represents a deck of playing cards."""
    def __init__(self):
        self.cards: List[Card] = [(rank, suit) for suit in SUITS for rank in RANKS]
        self.shuffle()

    def shuffle(self):
        """Shuffles the deck."""
        random.shuffle(self.cards)

    def deal(self) -> Card:
        """Deals one card from the top of the deck."""
        if not self.cards:
            # If the deck is empty, create and shuffle a new one.
            self.__init__()
        return self.cards.pop()

# --- Hand Class ---
class Hand:
    """Represents a hand of cards for a player or dealer."""
    def __init__(self):
        self.cards: List[Card] = []
        self.value = 0
        self.aces = 0

    def add_card(self, card: Card):
        """Adds a card to the hand and updates the value."""
        self.cards.append(card)
        rank = card[0]
        self.value += VALUES[rank]
        if rank == 'A':
            self.aces += 1
        self.adjust_for_ace()

    def adjust_for_ace(self):
        """Adjusts hand value if it's over 21 and contains an Ace."""
        while self.value > 21 and self.aces:
            self.value -= 10
            self.aces -= 1

    def __str__(self):
        """String representation of the hand."""
        return ' '.join([f"{card[0]}{card[1]}" for card in self.cards])

# --- Game State Class ---
class BlackjackGame:
    """Manages the state of a single blackjack game."""
    def __init__(self, bet_amount: int):
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.bet_amount = bet_amount
        self.game_over = False

    def start_game(self):
        """Deals the initial two cards to player and dealer."""
        self.player_hand.add_card(self.deck.deal())
        self.dealer_hand.add_card(self.deck.deal())
        self.player_hand.add_card(self.deck.deal())
        self.dealer_hand.add_card(self.deck.deal())

    def player_hits(self) -> bool:
        """Player takes another card. Returns True if player busts."""
        self.player_hand.add_card(self.deck.deal())
        if self.player_hand.value > 21:
            self.game_over = True
            return True  # Busted
        return False  # Not busted

    def dealer_plays(self):
        """Dealer plays their turn according to standard rules (hit on 16, stand on 17)."""
        while self.dealer_hand.value < 17:
            self.dealer_hand.add_card(self.deck.deal())
        self.game_over = True

    def determine_winner(self) -> Tuple[str, float]:
        """
        Determines the winner and the payout multiplier.
        Returns a tuple of (result_string, payout_multiplier).
        -1: Player loses bet, 0: Push, 1: Player wins, 1.5: Player gets Blackjack
        """
        player_score = self.player_hand.value
        dealer_score = self.dealer_hand.value

        is_player_blackjack = player_score == 21 and len(self.player_hand.cards) == 2
        is_dealer_blackjack = dealer_score == 21 and len(self.dealer_hand.cards) == 2

        if is_player_blackjack:
            return ("blackjack", 1.5) if not is_dealer_blackjack else ("push", 0)
        if player_score > 21:
            return "bust", -1
        if dealer_score > 21:
            return "win", 1
        if player_score > dealer_score:
            return "win", 1
        elif player_score < dealer_score:
            return "loss", -1
        else:  # Scores are equal
            return "push", 0