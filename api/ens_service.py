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



def _core_record_pairs(settings):
    return {
        settings.ENS_TEXT_API_KEY: settings.PUBLIC_BASE_URL,
        settings.ENS_TEXT_DEPLOYMENT_KEY: settings.APP_ENV,
    }


def update_core_records():
    """Update core ENS text records from current settings and return tx hashes."""
    settings = get_settings()
    service = ENSService()
    tx_hashes = {}
    for key, value in _core_record_pairs(settings).items():
        tx_hashes[key] = service.set_text(key, value)
    return tx_hashes


def read_core_records():
    """Read core ENS text records and return their current values."""
    settings = get_settings()
    service = ENSService()
    values = {}
    for key in _core_record_pairs(settings):
        values[key] = service.get_text(key)
    return values
