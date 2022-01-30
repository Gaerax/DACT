from pathlib import Path
from typing import List

from chia.types.blockchain_format.coin import Coin
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.types.blockchain_format.program import Program
from chia.types.condition_opcodes import ConditionOpcode
from chia.util.ints import uint64
from chia.util.hash import std_hash

from clvm.casts import int_to_bytes

import cdv.clibs as std_lib
from cdv.util.load_clvm import load_clvm

clibs_path: Path = Path(std_lib.__file__).parent
COMMUNITYFUND_MOD: Program = load_clvm("communityfund.clsp", "communityfund", search_paths=[clibs_path])


# Create a communityfund
def create_communityfund_puzzle(release_percentage: uint64, waittime: uint64, release_puzhash: bytes32) -> Program:
    return COMMUNITYFUND_MOD.curry(release_percentage, waittime, release_puzhash)


# Generate a solution to release of a communityfund
def solution_for_communityfund(cf_coin: Coin, contrib_amount: uint64) -> Program:
    return Program.to([cf_coin.puzzle_hash, cf_coin.amount, (cf_coin.amount + contrib_amount)])

# Return the condition to assert the announcement
def communityfund_announcement_assertion(cf_coin: Coin, contrib_amount: uint64) -> List:
    return [
        ConditionOpcode.ASSERT_COIN_ANNOUNCEMENT,
        std_hash(cf_coin.name() + int_to_bytes(cf_coin.amount + contrib_amount)),
    ]
