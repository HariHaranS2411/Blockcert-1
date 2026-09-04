import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

# Set UTF-8 encoding for console on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add root directory to python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load .env
env_file = BASE_DIR / '.env'
load_dotenv(env_file)

GANACHE_RPC_URL = os.environ.get('GANACHE_RPC_URL', 'http://127.0.0.1:8545')
ARTIFACT_PATH = BASE_DIR / 'contracts' / 'Certificate.json'


def update_env_file(key, value):
    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(f"{key}={value}\n")
        return

    with open(env_file, 'r') as f:
        content = f.read()

    pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
    if pattern.search(content):
        new_content = pattern.sub(f'{key}={value}', content)
    else:
        new_content = content.rstrip() + f"\n{key}={value}\n"

    with open(env_file, 'w') as f:
        f.write(new_content)


def deploy():
    print("=" * 60)
    print("  BlockCert - Smart Contract Deployment to Ganache")
    print("=" * 60)
    print(f"Connecting to Ganache RPC: {GANACHE_RPC_URL} ...")

    w3 = Web3(Web3.HTTPProvider(GANACHE_RPC_URL))
    if not w3.is_connected():
        print(f"\n[X] Error: Unable to connect to Ganache at {GANACHE_RPC_URL}")
        print("Please make sure Ganache is running (e.g. Ganache GUI or 'npx ganache') on port 8545.")
        sys.exit(1)

    print(f"Connected! Chain ID: {w3.eth.chain_id}, Block Number: {w3.eth.block_number}")

    if not ARTIFACT_PATH.exists():
        print(f"\n[X] Error: Artifact file not found at {ARTIFACT_PATH}")
        sys.exit(1)

    with open(ARTIFACT_PATH, 'r') as f:
        artifact = json.load(f)

    abi = artifact['abi']
    bytecode = artifact.get('bin') or artifact.get('bytecode')
    if not bytecode:
        print("\n[X] Error: Bytecode missing from artifact.")
        sys.exit(1)

    accounts = w3.eth.accounts
    if not accounts:
        print("\n[X] Error: No unlocked accounts available in Ganache.")
        sys.exit(1)

    deployer_account = accounts[0]
    print(f"Deployer / Issuer Account: {deployer_account}")
    print(f"Account Balance: {w3.from_wei(w3.eth.get_balance(deployer_account), 'ether')} ETH")

    print("\nDeploying Certificate contract...")
    CertificateContract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = CertificateContract.constructor().transact({'from': deployer_account})

    print(f"Transaction broadcasted: {tx_hash.hex()}")
    print("Waiting for transaction receipt...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    contract_address = receipt.contractAddress
    print(f"\n[OK] Contract successfully deployed to Ganache!")
    print(f" Contract Address : {contract_address}")
    print(f" Block Number     : {receipt.blockNumber}")
    print(f" Gas Used         : {receipt.gasUsed}")
    print(f" Issuer (Owner)   : {deployer_account}")

    # Update .env file
    update_env_file('CONTRACT_ADDRESS', contract_address)
    update_env_file('ISSUER_ADDRESS', deployer_account)
    print(f"\n Updated .env with CONTRACT_ADDRESS={contract_address} and ISSUER_ADDRESS={deployer_account}")
    print("=" * 60)
    return contract_address, deployer_account


if __name__ == '__main__':
    deploy()
