from typing import Final


CPT_PARASWAP: Final = 'paraswap'
SWAP_SIGNATURE: Final = b'\xe0\x03a\xd2\x07\xb2R\xa4d2>\xb2=E\xd4%\x83\xe3\x91\xf2\x03\x1a\xcd\xd2\xe9\xfa6\xef\xdd\xd4<\xb0'  # noqa: E501
BUY_SIGNATURE: Final = b'L\xc7\xe9^H\xafbi\x03\x13\xa0s>\x930\x8a\xc9\xa73&\xbc<)\xf1x\x8b\x11\x91\xc3v\xd5\xb6'  # noqa: E501

SWAP_ON_UNISWAP_V2_FORK: Final = b'\x0b\x86\xa4\xc1'
SWAP_ON_UNISWAP_V2_FACTORY: Final = b'\xf5f\x104'
SWAP_ON_UNISWAP_V2_FORK_WITH_PERMIT: Final = b'n\x91S\x8b'
BUY_ON_UNISWAP_V2_FORK: Final = b'\xb2\xf1\xe6\xdb'
DIRECT_UNI_V3_SWAP: Final = b'\xa6\x88m\xa9'
DIRECT_CURVE_V1_SWAP: Final = b'8e\xbd\xe6'
DIRECT_CURVE_V2_SWAP: Final = b'X\xf1Q\x00'
DIRECT_BALANCER_V2_GIVEN_IN_SWAP: Final = b'\xb2/M\xb8'
