import os
import sqlite3
import time
from flask import Flask, request, jsonify, render_template
from web3 import Web3
from dotenv import load_dotenv
from flask_cors import CORS
import json # Importa a biblioteca json

# --- 1. CONFIGURAÇÃO INICIAL ---
load_dotenv()
app = Flask(__name__)
CORS(app)

# Valida se a URL RPC foi definida
rpc_url = os.getenv("ARBITRUM_RPC_URL")
if not rpc_url:
    print("ERRO CRÍTICO: A variável ARBITRUM_RPC_URL não está definida no arquivo .env")
    exit()
w3 = Web3(Web3.HTTPProvider(rpc_url))

# Valida a chave privada e carrega a conta do faucet
try:
    private_key = os.getenv("FAUCET_PRIVATE_KEY")
    if not private_key:
        raise TypeError("A variável FAUCET_PRIVATE_KEY está vazia ou não foi definida.")
    FAUCET_ACCOUNT = w3.eth.account.from_key(private_key)
    print(f"Faucet carregado com o endereço: {FAUCET_ACCOUNT.address}")
except TypeError as e:
    print(f"ERRO CRÍTICO: {e}")
    exit()

# Valida e prepara o endereço do contrato do token
raw_token_address = os.getenv("TOKEN_CONTRACT_ADDRESS")
if not raw_token_address:
    print("ERRO CRÍTICO: A variável TOKEN_CONTRACT_ADDRESS não está definida no arquivo .env")
    exit()
TOKEN_CONTRACT_ADDRESS = Web3.to_checksum_address(raw_token_address)

# ABI completa do contrato comUSD
TOKEN_ABI = [
    {"inputs":[{"internalType":"address","name":"initialOwner","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"allowance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientAllowance","type":"error"},
    {"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"uint256","name":"balance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientBalance","type":"error"},
    {"inputs":[{"internalType":"address","name":"approver","type":"address"}],"name":"ERC20InvalidApprover","type":"error"},
    {"inputs":[{"internalType":"address","name":"receiver","type":"address"}],"name":"ERC20InvalidReceiver","type":"error"},
    {"inputs":[{"internalType":"address","name":"sender","type":"address"}],"name":"ERC20InvalidSender","type":"error"},
    {"inputs":[{"internalType":"address","name":"spender","type":"address"}],"name":"ERC20InvalidSpender","type":"error"},
    {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"OwnableInvalidOwner","type":"error"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"OwnableUnauthorizedAccount","type":"error"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"account","type":"address"}],"name":"AddressExcludedFromFee","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"account","type":"address"}],"name":"AddressIncludedInFee","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"owner","type":"address"},{"indexed":True,"internalType":"address","name":"spender","type":"address"},{"indexed":False,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint256","name":"newFeeBps","type":"uint256"}],"name":"FeeRateUpdated","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":True,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"account","type":"address"}],"name":"Paused","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"from","type":"address"},{"indexed":True,"internalType":"address","name":"to","type":"address"},{"indexed":False,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"account","type":"address"}],"name":"Unpaused","type":"event"},
    {"inputs":[],"name":"FEE_DENOMINATOR","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"MAX_FEE_BPS","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"MAX_SUPPLY","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"burnFeeBps","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"pure","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"excludeFromFee","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"includeInFee","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"isExcludedFromFee","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"pause","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"paused","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"_newFeeBps","type":"uint256"}],"name":"setBurnFee","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"unpause","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

TOKEN_CONTRACT = w3.eth.contract(address=TOKEN_CONTRACT_ADDRESS, abi=TOKEN_ABI)

# --- 2. PARÂMETROS DO FAUCET ---
AMOUNT_TO_SEND = w3.to_wei(100, 'gwei')
COOLDOWN_SECONDS = 24 * 60 * 60
CHAIN_ID = 42161

# --- 3. BANCO DE DADOS PARA CONTROLE ---
def init_db():
    conn = sqlite3.connect('faucet_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            claim_time INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 4. ROTAS DA APLICAÇÃO WEB (API) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/claim', methods=['POST'])
def claim_tokens():
    try:
        data = request.get_json()
        user_address = data.get('address')
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        if not user_address or not Web3.is_address(user_address):
            return jsonify({"error": "Endereço de carteira inválido fornecido."}), 400

        checksum_user_address = Web3.to_checksum_address(user_address)

        conn = sqlite3.connect('faucet_data.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT claim_time FROM claims WHERE wallet_address = ? OR ip_address = ? ORDER BY claim_time DESC LIMIT 1",
            (checksum_user_address, user_ip)
        )
        last_claim = cursor.fetchone()

        if last_claim and (time.time() - last_claim[0] < COOLDOWN_SECONDS):
            conn.close()
            return jsonify({"error": "Limite de resgate atingido. Por favor, tente novamente em 24 horas."}), 429

        print(f"Enviando {w3.from_wei(AMOUNT_TO_SEND, 'gwei')} comUSD para {checksum_user_address}...")
        
        nonce = w3.eth.get_transaction_count(FAUCET_ACCOUNT.address)
        
        tx_build = TOKEN_CONTRACT.functions.transfer(
            checksum_user_address,
            AMOUNT_TO_SEND
        ).build_transaction({
            'chainId': CHAIN_ID,
            'gas': 200000,
            'nonce': nonce,
        })

        signed_tx = w3.eth.account.sign_transaction(tx_build, private_key=FAUCET_ACCOUNT.key)
        
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        cursor.execute(
            "INSERT INTO claims (wallet_address, ip_address, claim_time) VALUES (?, ?, ?)",
            (checksum_user_address, user_ip, int(time.time()))
        )
        conn.commit()
        conn.close()

        print(f"Sucesso! Hash da transação: {w3.to_hex(tx_hash)}")
        return jsonify({"success": True, "tx_hash": w3.to_hex(tx_hash)})

    except Exception as e:
        # --- CORREÇÃO APLICADA AQUI ---
        # Imprime o erro técnico detalhado no log do servidor (para você ver)
        print(f"ERRO no resgate: {e}")
        
        # Retorna uma mensagem de erro genérica e amigável para o usuário final
        return jsonify({"error": "ERRO! Não foi possível processar a solicitação no momento. Tente novamente mais tarde."}), 500

# --- 5. INICIAR O SERVIDOR ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)