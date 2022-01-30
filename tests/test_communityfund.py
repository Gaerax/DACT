import pytest

from typing import Dict, List, Optional

from chia.types.blockchain_format.coin import Coin
from chia.types.spend_bundle import SpendBundle
from chia.types.condition_opcodes import ConditionOpcode
from chia.util.ints import uint64

from communityfund.communityfund_drivers import (
    create_communityfund_puzzle,
    solution_for_communityfund,
    communityfund_announcement_assertion,
)

from cdv.test import CoinWrapper
from cdv.test import setup as setup_test


class TestStandardTransaction:
    @pytest.fixture(scope="function")
    async def setup(self):
        network, alice, bob = await setup_test()
        await network.farm_block()
        yield network, alice, bob

    async def make_and_spend_communityfund(self, network, alice, bob, CONTRIBUTION_AMOUNT) -> Dict[str, List[Coin]]:
        # Get our alice wallet some money
        await network.farm_block(farmer=alice)

        # This will use one mojo to create our communityfund on the blockchain.
        communityfund_coin: Optional[CoinWrapper] = await alice.launch_smart_coin(
            create_communityfund_puzzle(1, 2, bob.puzzle_hash)
        )

        # This retrieves us a coin that is at least 500 mojos.
        contribution_coin: Optional[CoinWrapper] = await alice.choose_coin(CONTRIBUTION_AMOUNT)

        # Make sure everything succeeded
        if not communityfund_coin or not contribution_coin:
            raise ValueError("Something went wrong launching/choosing a coin")

        # This is the spend of the community fund coin.  We use the driver code to create the solution.
        communityfund_spend: SpendBundle = await alice.spend_coin(
            communityfund_coin,
            pushtx=False,
            args=solution_for_communityfund(communityfund_coin.as_coin(), CONTRIBUTION_AMOUNT),
        )
        # This is the spend of a standard coin.  We simply spend to ourselves but minus the CONTRIBUTION_AMOUNT.
        contribution_spend: SpendBundle = await alice.spend_coin(
            contribution_coin,
            pushtx=False,
            amt=(contribution_coin.amount - CONTRIBUTION_AMOUNT),
            custom_conditions=[
                [
                    ConditionOpcode.CREATE_COIN,
                    contribution_coin.puzzle_hash,
                    (contribution_coin.amount - CONTRIBUTION_AMOUNT),
                ],
                communityfund_announcement_assertion(communityfund_coin.as_coin(), CONTRIBUTION_AMOUNT),
            ],
        )

        # Aggregate them to make sure they are spent together
        combined_spend = SpendBundle.aggregate([contribution_spend, communityfund_spend])

        result = await network.push_tx(combined_spend)
        return result

    @pytest.mark.asyncio
    async def test_communityfund_contribution(self, setup):
        network, alice, bob = setup
        try:
            result: Dict[str, List[Coin]] = await self.make_and_spend_communityfund(network, alice, bob, 500000000000)

            assert "error" not in result

            # Make sure there is exactly one communityfund with the new amount
            filtered_result: List[Coin] = list(
                filter(
                    lambda addition: (addition.amount == 500000000001)
                    and (
                        addition.puzzle_hash == create_communityfund_puzzle(1, 2, bob.puzzle_hash).get_tree_hash()
                    ),
                    result["additions"],
                )
            )
            assert len(filtered_result) == 1
        finally:
            await network.close()

    @pytest.mark.asyncio
    async def test_communityfund_release(self, setup):
        network, alice, bob = setup
        try:
            result: Dict[str, List[Coin]] = await self.make_and_spend_communityfund(network, alice, bob, 0)
            print("Release:")
            print(result)

            assert "error" in result
            
        finally:
            await network.close()
