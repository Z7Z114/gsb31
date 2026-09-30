"""
Regression suite for the Jack engine (happy paths only).

Everything asserted here is already correct behaviour. It must stay green: do not
weaken, delete or skip these tests, and do not change the expectations to match a
broken implementation. Runs offline, on plain Python + numpy.
"""
import unittest

import pytest

from BasicStrategy import BasicStrategy as bs
from Card import Card
from Hand import Hand
from Jack import Jack
from Player import Player
from Shoe import Shoe
from Utils import Utils


class FakeShoe:
    """Deals the given cards in order; same interface as Shoe."""

    def __init__(self, names):
        self.cards = [Card(name) for name in names]
        self.end_of_shoe = False

    def pop(self):
        return self.cards.pop(0)


def value(cards):
    return Utils.card_value(cards)


# --- shoe ------------------------------------------------------------------


def test_shoe_holds_eight_decks():
    shoe = Shoe()
    assert len(shoe.cards) == 8 * 52
    assert isinstance(shoe.cards[0], Card)


def test_shoe_reports_the_end_of_the_shoe():
    shoe = Shoe()
    for _ in range(8 * 52):
        shoe.pop()
    assert shoe.end_of_shoe is False
    shoe.pop()
    assert shoe.end_of_shoe is True
    assert len(shoe.cards) == 0


# --- dealing ---------------------------------------------------------------


def test_deal_cards_order():
    p1 = Player(Hand([]))
    p2 = Player(Hand([]))
    dealer_hand = []
    shoe = FakeShoe(["D2", "D3", "D4", "D5", "D6", "D7"])

    Jack.deal_cards(shoe, [p1, p2], dealer_hand)

    assert [c.name for c in p1.hands[0].cards] == ["D2", "D5"]
    assert [c.name for c in p2.hands[0].cards] == ["D3", "D6"]
    assert [c.name for c in dealer_hand] == ["D4", "D7"]
    assert len(shoe.cards) == 0


# --- one player's turn -----------------------------------------------------


def test_twenty_stands_without_drawing():
    player = Player(Hand([Card("HJ"), Card("HQ")]))
    shoe = FakeShoe(["CJ"])

    Jack.turn(shoe, player, 0, Card("S2"))

    assert player.hands[0].status == "stand"
    assert len(player.hands[0].cards) == 2
    assert len(shoe.cards) == 1


def test_low_hand_hits_until_it_stands():
    player = Player(Hand([Card("H2"), Card("H3")]))
    shoe = FakeShoe(["S9", "S3"])

    Jack.turn(shoe, player, 0, Card("S7"))

    assert player.hands[0].status == "stand"
    assert value(player.hands[0].cards) == 17
    assert len(player.hands[0].cards) == 4


def test_hand_over_twenty_one_is_busted():
    player = Player(Hand([Card("HJ"), Card("HQ"), Card("H3")]))

    Jack.turn(FakeShoe([]), player, 0, Card("S2"))

    assert player.hands[0].status == "busted"


def test_two_card_twenty_one_is_a_blackjack():
    player = Player(Hand([Card("HQ"), Card("HA")]))

    Jack.turn(FakeShoe([]), player, 0, Card("S2"))

    assert player.hands[0].status == "blackjack"


def test_double_down_draws_exactly_one_card():
    player = Player(Hand([Card("H4"), Card("H6")]))
    shoe = FakeShoe(["CJ"])

    Jack.turn(shoe, player, 0, Card("S2"))

    assert player.hands[0].status == "ddown"
    assert player.hands[0].units == 2
    assert len(player.hands[0].cards) == 3
    assert player.units_spent == 2
    assert len(shoe.cards) == 0


def test_split_creates_two_equal_hands():
    player = Player(Hand([Card("H8"), Card("D8")]))
    shoe = FakeShoe(["H9", "H10"])

    Jack.turn(shoe, player, 0, Card("S2"))

    assert sorted(player.hands.keys()) == [0, 1]
    assert player.hands[0].status == "stand"
    assert player.hands[1].status == "stand"
    assert len(player.hands[0].cards) == 2
    assert len(player.hands[1].cards) == 2
    assert player.hands[0].units == 1
    assert player.hands[1].units == 1
    assert player.units_spent == 2
    assert sum(h.units for h in player.hands.values()) == player.units_spent


# --- the dealer ------------------------------------------------------------


def test_dealer_stands_on_soft_seventeen():
    dealer_hand = [Card("HA"), Card("H6")]
    shoe = FakeShoe(["C10"])

    Jack.up_to_17(shoe, dealer_hand)

    assert value(dealer_hand) == 17
    assert len(shoe.cards) == 1


def test_dealer_draws_until_seventeen():
    dealer_hand = [Card("H10"), Card("H6")]
    shoe = FakeShoe(["C5"])

    Jack.up_to_17(shoe, dealer_hand)

    assert value(dealer_hand) == 21
    assert len(shoe.cards) == 0


# --- settling a round ------------------------------------------------------


@pytest.mark.parametrize(
    "player_status,player_cards,dealer_cards,expected",
    [
        ("stand", ["HJ", "H9"], ["H10", "C7"], 2),        # 19 beats 17
        ("stand", ["H9", "H9"], ["H9", "C9"], 1),         # push
        ("stand", ["H2", "C3"], ["H9", "C9"], 0),         # 5 loses to 19
        ("busted", ["HJ", "HQ", "H3"], ["H10", "C7"], 0),  # bust loses even if the dealer is worse
        ("blackjack", ["HA", "D10"], ["H10", "C7"], 2.5),  # 3:2
        ("unnat", ["H2", "C3", "C10", "D6"], ["H10", "C7"], 2),  # 21 in four cards is paid like a win
    ],
)
def test_payouts(player_status, player_cards, dealer_cards, expected):
    player = Player(Hand([Card(name) for name in player_cards]))
    player.hands[0].status = player_status

    Jack.resolve_hands(player, [Card(name) for name in dealer_cards])

    assert player.recent_winloss == [expected]


def test_dealer_blackjack_pushes_against_a_player_blackjack():
    player = Player(Hand([Card("HA"), Card("D10")]))
    player.hands[0].status = "blackjack"

    Jack.resolve_hands(player, [Card("HA"), Card("C10")])

    assert player.recent_winloss == [1]


def test_surrender_loses_half_the_bet():
    player = Player(Hand([Card("H9"), Card("C7")]))
    player.hands[0].status = "sur"

    Jack.resolve_hands(player, [Card("H10"), Card("C7")])

    assert player.recent_winloss == [0.5]


# --- a whole round ---------------------------------------------------------


def test_round_is_played_and_settled():
    player = Player()
    shoe = FakeShoe(["H10", "D5", "H9", "D6", "C6"])

    Jack.game(shoe, [player])

    assert player.hands[0].status == "stand"
    assert player.recent_winloss == [2]
    assert len(shoe.cards) == 0


def test_results_accumulate_until_the_player_is_reset():
    player = Player()
    for _ in range(3):
        Jack.game(FakeShoe(["H10", "D5", "H9", "D6", "C6"]), [player])
        player.clear_hands()

    assert player.recent_winloss == [2, 2, 2]

    player.reset()
    assert player.recent_winloss == []
    assert player.units_spent == 0
    assert len(player.hands) == 1


def test_strategy_lookup_rows_and_columns():
    assert bs.lookup_upcard_idx(Card("DA")) == 9
    assert bs.lookup_upcard_idx(Card("S9")) == 7
    assert bs.lookup_normal_row([Card("H6"), Card("C7")]) == 3
    assert bs.lookup_split_row([Card("H2"), Card("C2")]) == 8
    assert bs.lookup_soft_row([Card("HA"), Card("C2")]) == 5
