from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import (
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    hex_or_bytes_to_str,
)

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

# Constants for the Agave events --> derived from a txs topic as bytes.fromhex('')
DEPOSIT = b'\xdehW!\x95D\xbb[wF\xf4\x8e\xd3\x0b\xe68o\xef\xc6\x1b/\x86L\xac\xf5Y\x89;\xf5\x0f\xd9Q' # noqa: E501
WITHDRAW = b'1\x15\xd1D\x9a{s,\x98l\xba\x18$N\x89zE\x0fa\xe1\xbb\x8dX\x9c\xd2\xe6\x9el\x89$\xf9\xf7'  # noqa: E501
BORROW = b'\xc6\xa8\x980\x9e\x82>\xe5\x0b\xacd\xe4\\\xa8\xad\xbaf\x90\xe9\x9exA\xc4]uN*8\xe9\x01\x9d\x9b'  # noqa: E501
REPAY = b'\xa54\xc8\xdb\xe7\x1f\x87\x1f\x9f50\xe9zt`\x1f\xea\x17\xb4&\xca\xe0.\x1cZ\xeeB\xc9lx@Q'  # noqa: E501
LIQUIDATION_CALL = b'\x00\xfc\xbcUm\xd8>8\xc8\xe1EE{\xb1AaRV\xcf\xe5\xa7s<\x97\xd3\xe5\xc2X\x8d\x06U\x1f'  # noqa: E501
ENABLE_COLLATERAL = b'\x00\x05\x8aV\xea\x94e<\xdfO\x15-"z\xce"\xd4\xc0\n\xd9\x9e*C\xf5\x8c\xb7\xd9\xe3\xfe\xb2\x95\xf2' # noqa: E501
DISABLE_COLLATERAL = b'D\xc5\x8d\x816[f\xddK\x1a\x7f6\xc2Z\xa9{\x8cq\xc3a\xeeI7\xad\xc1\xa0\x00\x00"}\xb5\xdd'  # noqa: E501


class AgaveDecoder(DecoderInterface):

    def _decode_collateral_events(
            self,
            token: 'EvmToken',
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
    ) -> Optional['EvmEvent']:
        pass

    def _decode_deposit(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        pass
    
    def _decode_withdrawal(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        pass

    def _decode_borrow(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        pass

    def _decode_liquidation(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        pass


    def _decode_repay(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
    ) -> None:
        pass


    """
        Goes through the  Lending Pool events and decodes them
    """    
    def _decode_lending_pool_events(self, context: DecoderContext) -> DecodingOutput:
        
        if context.tx_log.topics[0] not in (LIQUIDATION_CALL, ENABLE_COLLATERAL, DISABLE_COLLATERAL, DEPOSIT, WITHDRAW, BORROW, REPAY):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        if context.tx_log.topics[0] == LIQUIDATION_CALL:
            # the liquidation event has two tokens and needs to be checked per event
            self._decode_liquidation(context.tx_log, context.decoded_events)
            return DEFAULT_DECODING_OUTPUT

        token = EvmToken(evm_address_to_identifier(
            address=hex_or_bytes_to_address(context.tx_log.topics[1]),
            token_type=EvmTokenKind.ERC20,
            chain_id=self.evm_inquirer.chain_id,
        ))

        if context.tx_log.topics[0] in (ENABLE_COLLATERAL, DISABLE_COLLATERAL):
            event = self._decode_collateral_events(token, context.transaction, context.tx_log)
            return DecodingOutput(event=event)
        if context.tx_log.topics[0] == DEPOSIT:
            self._decode_deposit(token, context.tx_log, context.decoded_events)
        elif context.tx_log.topics[0] == WITHDRAW:
            self._decode_withdrawal(token, context.tx_log, context.decoded_events)
        elif context.tx_log.topics[0] == BORROW:
            self._decode_borrow(token, context.tx_log, context.decoded_events)
        else:  # Repay
            self._decode_repay(token, context.tx_log, context.decoded_events)

        return DEFAULT_DECODING_OUTPUT



    # ------------------------ DecoderInterface methods ------------------------

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            string_to_evm_address("x"): (self._decode_lending_pool_events,), # noqa: E501
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier="x", label="x", image='aave.svg'),)