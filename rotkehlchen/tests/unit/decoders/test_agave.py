from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.aave.constants import CPT_AAVE_V1, CPT_AAVE_V2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_REN, A_WETH
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
ADDY2 = '0x5727c0481b90a129554395937612d8b9301D6c7b'

@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0xeccf11f03cefe8a68bb01caf66e76ceefeaaee5e')]])  # noqa: E501
def test_agave_borrow(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x6c8af2a4157632e33fac9d94a03619f54d318ce1254998aabc5384053eb98ffb
    https://gnosisscan.io/tx/0x1d0bcd6456e6a00425bf2149308bee5a16baa1d27c4e62caa63b0f2768a4e29a
    """
    tx_hex = '0x1d0bcd6456e6a00425bf2149308bee5a16baa1d27c4e62caa63b0f2768a4e29a'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0xeccf11f03cefe8a68bb01caf66e76ceefeaaee5e')
    
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=user_address,
            notes='Burned 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=307,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xcd9D82d33bd737De215cDac57FE2F7f04DF77FE0'),
            balance=Balance(amount=FVal(100000)),
            location_label=user_address,
            notes='Receive 100000 variableDebtREN from AAVE v2',
            counterparty=CPT_AAVE_V2,
            extra_data=None,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=310,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_REN,
            balance=Balance(amount=FVal(100000)),
            location_label=user_address,
            notes='Borrow 100000 REN from AAVE v2 with variable APY 0.80%',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0xCC12AbE4ff81c9378D670De1b57F8e0Dd228D77a'),
        ),
    ]
    assert events == expected_events