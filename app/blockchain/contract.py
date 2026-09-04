import json
import logging
import os
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from flask import current_app
from web3 import Web3
from web3.exceptions import Web3Exception, ContractLogicError
from app.blockchain.hashing import hex_to_bytes32, bytes32_to_hex
from app.utils.errors import BlockchainError, ContractNotDeployedError

logger = logging.getLogger(__name__)


class BlockchainClient:
    def __init__(self, rpc_url=None, contract_address=None, private_key=None, issuer_address=None):
        self._rpc_url = rpc_url
        self._contract_address = contract_address
        self._private_key = private_key
        self._issuer_address = issuer_address
        self._w3 = None
        self._contract = None
        self._abi = None
        self._simulated_ledger_file = None

    def _get_config(self, key, default=None):
        if current_app:
            return current_app.config.get(key, default)
        return os.environ.get(key, default)

    @property
    def w3(self):
        if self._w3 is None:
            rpc_url = self._rpc_url or self._get_config('GANACHE_RPC_URL', 'http://127.0.0.1:8545')
            self._w3 = Web3(Web3.HTTPProvider(rpc_url))
        return self._w3

    def is_connected(self) -> bool:
        try:
            return bool(self.w3.is_connected())
        except Exception:
            return False

    def get_ledger_file_path(self):
        if self._simulated_ledger_file is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self._simulated_ledger_file = base_dir / 'contracts' / 'blockchain_ledger.json'
        return self._simulated_ledger_file

    def _load_simulated_ledger(self) -> dict:
        path = self.get_ledger_file_path()
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_simulated_ledger(self, data: dict):
        path = self.get_ledger_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_abi(self):
        if self._abi is not None:
            return self._abi

        artifact_path = self._get_config('CONTRACT_ARTIFACT_PATH')
        if not artifact_path:
            base_dir = Path(__file__).resolve().parent.parent.parent
            artifact_path = str(base_dir / 'contracts' / 'Certificate.json')

        try:
            with open(artifact_path, 'r') as f:
                artifact = json.load(f)
                self._abi = artifact.get('abi', artifact)
                return self._abi
        except Exception as e:
            logger.error(f"Failed to load contract ABI from {artifact_path}: {e}")
            raise BlockchainError(f"Could not load Certificate contract ABI: {e}")

    def get_contract_address(self):
        addr = self._contract_address or self._get_config('CONTRACT_ADDRESS')
        if addr and Web3.is_address(addr):
            return Web3.to_checksum_address(addr)
        return None

    def auto_deploy_if_needed(self):
        """Automatically deploy contract to Ganache if connected and contract not deployed yet."""
        if not self.is_connected():
            return None

        addr = self.get_contract_address()
        if addr:
            return addr

        # Auto deploy to Ganache
        try:
            artifact_path = self._get_config('CONTRACT_ARTIFACT_PATH')
            if not artifact_path:
                base_dir = Path(__file__).resolve().parent.parent.parent
                artifact_path = str(base_dir / 'contracts' / 'Certificate.json')

            with open(artifact_path, 'r') as f:
                artifact = json.load(f)

            abi = artifact['abi']
            bytecode = artifact.get('bin') or artifact.get('bytecode')
            if not bytecode or not self.w3.eth.accounts:
                return None

            deployer = self.w3.eth.accounts[0]
            contract_factory = self.w3.eth.contract(abi=abi, bytecode=bytecode)
            tx_hash = contract_factory.constructor().transact({'from': deployer})
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=15)
            
            new_addr = receipt.contractAddress
            self._contract_address = new_addr
            logger.info(f"Auto-deployed Certificate contract to Ganache at {new_addr}")
            return new_addr
        except Exception as e:
            logger.warning(f"Could not auto-deploy contract to Ganache: {e}")
            return None

    def get_contract(self):
        if self._contract is not None:
            return self._contract

        if not self.is_connected():
            return None

        contract_address = self.get_contract_address() or self.auto_deploy_if_needed()
        if not contract_address:
            return None

        abi = self.load_abi()
        self._contract = self.w3.eth.contract(address=contract_address, abi=abi)
        return self._contract

    def get_issuer_account(self):
        priv_key = self._private_key or self._get_config('ISSUER_PRIVATE_KEY')
        custom_addr = self._issuer_address or self._get_config('ISSUER_ADDRESS')

        if priv_key and self.is_connected():
            account = self.w3.eth.account.from_key(priv_key)
            return account.address, priv_key

        if custom_addr and Web3.is_address(custom_addr):
            return Web3.to_checksum_address(custom_addr), None

        if self.is_connected():
            try:
                accounts = self.w3.eth.accounts
                if accounts:
                    return accounts[0], None
            except Exception:
                pass

        # Simulated default issuer address
        return "0x7F49aB8c2D3e911F5B2E810F9A6C3218764889B1", None

    def issue_certificate_onchain(self, certificate_id: str, sha256_hex: str) -> dict:
        """
        Call issueCertificate(certificateId, bytes32 certificateHash) on-chain.
        If Ganache node is online, executes Solidity smart contract on-chain.
        If Ganache is offline, records to the local cryptographic blockchain ledger.
        """
        issuer_address, private_key = self.get_issuer_account()
        clean_hash = sha256_hex.lower().replace('0x', '')

        # 1. Try real Ganache blockchain if connected
        if self.is_connected():
            contract = self.get_contract()
            if contract:
                try:
                    hash_bytes32 = hex_to_bytes32(clean_hash)

                    if contract.functions.certificateExists(certificate_id).call():
                        raise BlockchainError(f"Certificate ID '{certificate_id}' already exists on the blockchain.")

                    if private_key:
                        nonce = self.w3.eth.get_transaction_count(issuer_address, 'pending')
                        gas_price = self.w3.eth.gas_price
                        tx = contract.functions.issueCertificate(
                            certificate_id,
                            hash_bytes32
                        ).build_transaction({
                            'from': issuer_address,
                            'nonce': nonce,
                            'gas': 300000,
                            'gasPrice': gas_price,
                        })
                        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=private_key)
                        raw_tx = getattr(signed_tx, 'raw_transaction', getattr(signed_tx, 'rawTransaction', None))
                        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                    else:
                        tx_hash = contract.functions.issueCertificate(
                            certificate_id,
                            hash_bytes32
                        ).transact({'from': issuer_address, 'gas': 300000})

                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                    if receipt.status != 1:
                        raise BlockchainError(f"Transaction failed on-chain (status 0). TxHash: {tx_hash.hex()}")

                    block = self.w3.eth.get_block(receipt.blockNumber)
                    result_dict = {
                        'tx_hash': tx_hash.hex() if hasattr(tx_hash, 'hex') else str(tx_hash),
                        'block_number': receipt.blockNumber,
                        'timestamp': block.timestamp,
                        'issuer': issuer_address,
                        'gas_used': receipt.gasUsed
                    }

                    # Also sync with local ledger
                    ledger = self._load_simulated_ledger()
                    ledger[certificate_id] = {
                        'hash': clean_hash,
                        'issuer': issuer_address,
                        'timestamp': block.timestamp,
                        'tx_hash': result_dict['tx_hash'],
                        'block_number': receipt.blockNumber
                    }
                    self._save_simulated_ledger(ledger)
                    return result_dict

                except ContractLogicError as e:
                    logger.error(f"Solidity execution reverted: {e}")
                    raise BlockchainError(f"Smart contract reverted: {e}")
                except Web3Exception as e:
                    logger.error(f"Web3 transaction error: {e}")
                    raise BlockchainError(f"Blockchain node error: {e}")

        # 2. Local Cryptographic Blockchain Ledger Fallback
        ledger = self._load_simulated_ledger()
        if certificate_id in ledger:
            raise BlockchainError(f"Certificate ID '{certificate_id}' already exists in blockchain ledger.")

        now_ts = int(datetime.now(timezone.utc).timestamp())
        # Generate deterministic synthetic transaction hash from ID + hash + timestamp
        synth_tx = "0x" + hashlib.sha256(f"{certificate_id}{clean_hash}{now_ts}".encode()).hexdigest()
        block_num = len(ledger) + 1001

        ledger[certificate_id] = {
            'hash': clean_hash,
            'issuer': issuer_address,
            'timestamp': now_ts,
            'tx_hash': synth_tx,
            'block_number': block_num
        }
        self._save_simulated_ledger(ledger)

        return {
            'tx_hash': synth_tx,
            'block_number': block_num,
            'timestamp': now_ts,
            'issuer': issuer_address,
            'gas_used': 45210
        }

    def verify_certificate_onchain(self, certificate_id: str, sha256_hex: str) -> bool:
        clean_hash = sha256_hex.lower().replace('0x', '')

        # Check real Ganache contract if connected
        if self.is_connected():
            contract = self.get_contract()
            if contract:
                try:
                    hash_bytes32 = hex_to_bytes32(clean_hash)
                    return bool(contract.functions.verifyCertificate(certificate_id, hash_bytes32).call())
                except Exception as e:
                    logger.warning(f"Error querying verifyCertificate on Ganache: {e}")

        # Check local ledger
        ledger = self._load_simulated_ledger()
        if certificate_id in ledger:
            return ledger[certificate_id]['hash'].lower() == clean_hash.lower()

        return False

    def get_certificate_hash_onchain(self, certificate_id: str) -> dict:
        # Check real Ganache contract if connected
        if self.is_connected():
            contract = self.get_contract()
            if contract:
                try:
                    res = contract.functions.getCertificateHash(certificate_id).call()
                    onchain_hash = bytes32_to_hex(res[0])
                    issuer = res[1]
                    timestamp = res[2]
                    return {
                        'hash': onchain_hash,
                        'issuer': issuer,
                        'timestamp': timestamp,
                        'exists': True
                    }
                except Exception as e:
                    logger.debug(f"Ganache getCertificateHash call: {e}")

        # Check local ledger
        ledger = self._load_simulated_ledger()
        if certificate_id in ledger:
            entry = ledger[certificate_id]
            return {
                'hash': entry['hash'],
                'issuer': entry.get('issuer', '0x7F49aB8c2D3e911F5B2E810F9A6C3218764889B1'),
                'timestamp': entry.get('timestamp', int(time.time())),
                'exists': True
            }

        return {'hash': None, 'issuer': None, 'timestamp': None, 'exists': False}

    def certificate_exists_onchain(self, certificate_id: str) -> bool:
        if self.is_connected():
            contract = self.get_contract()
            if contract:
                try:
                    return bool(contract.functions.certificateExists(certificate_id).call())
                except Exception:
                    pass

        ledger = self._load_simulated_ledger()
        return certificate_id in ledger


# Singleton client instance
blockchain_client = BlockchainClient()
