from web3 import Web3
from eth_account import Account
from eth_utils import keccak
from typing import Optional
from .settings import get_settings


ENS_REGISTRY_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "node", "type": "bytes32"}],
        "name": "resolver",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    }
]

PUBLIC_RESOLVER_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "node", "type": "bytes32"},
            {"name": "key", "type": "string"},
        ],
        "name": "text",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "node", "type": "bytes32"},
            {"name": "key", "type": "string"},
            {"name": "value", "type": "string"},
        ],
        "name": "setText",
        "outputs": [],
        "type": "function",
    },
]


def namehash(name: str) -> bytes:
    node = b"\x00" * 32
    if name:
        labels = name.split(".")
        for label in reversed(labels):
            node = keccak(node + keccak(text=label))
    return node


class ENSService:
    def __init__(self):
        settings = get_settings()
        self.w3 = Web3(Web3.HTTPProvider(settings.MAINNET_RPC_URL))
        self.registry = self.w3.eth.contract(
            address=settings.ENS_REGISTRY_ADDRESS, abi=ENS_REGISTRY_ABI
        )
        self.name = settings.ENS_NAME
        self.node = namehash(self.name)
        self.account = (
            Account.from_key(settings.ENS_PRIVATE_KEY)
            if settings.ENS_PRIVATE_KEY
            else None
        )

    def get_resolver(self):
        resolver_address = self.registry.functions.resolver(self.node).call()
        return self.w3.eth.contract(address=resolver_address, abi=PUBLIC_RESOLVER_ABI)

    def get_text(self, key: str) -> Optional[str]:
        resolver = self.get_resolver()
        return resolver.functions.text(self.node, key).call()

    def set_text(self, key: str, value: str) -> str:
        if not self.account:
            raise Exception("No ENS private key configured")

        resolver = self.get_resolver()
        tx = resolver.functions.setText(self.node, key, value).build_transaction(
            {
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 200000,
                "gasPrice": self.w3.to_wei("20", "gwei"),
            }
        )

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()
