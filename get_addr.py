from wallet_transaction import Wallet
w0 = Wallet(private_key_pem=open("wallets/wallet_8000.pem").read())
w1 = Wallet(private_key_pem=open("wallets/wallet_8001.pem").read())
print("P8000 (User):", w0.public_key)
print("P8001 (Me):", w1.public_key)
