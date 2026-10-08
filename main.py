import os
import random
import json
import websocket
from flask import Flask, request, jsonify

app = Flask(__name__)

# Récupération du SSID sauvegardé dans les variables cloud
SSID = os.environ.get("POCKET_OPTION_SSID")

def send_pocket_order(asset, action, amount, duration):
    """Envoie l'ordre d'achat/vente à Pocket Option via WebSocket."""
    ws_url = "wss://api-fin.po.market/socket.io/?EIO=4&transport=websocket"
    
    try:
        ws = websocket.create_connection(ws_url)
        # 1. Envoi du message d'authentification
        ws.send(SSID)
        
        # 2. Construction de la commande de trade
        direction = "call" if action.lower() in ["call", "buy"] else "put"
        
        trade_msg = f'42["openOrder", {{"asset": "{asset}", "amount": {amount}, "action": "{direction}", "isDemo": 1, "requestId": {random.randint(100000, 999999)}, "time": {duration}}}]'
        
        # 3. Envoi de l'ordre
        ws.send(trade_msg)
        ws.close()
        return True, "Ordre envoyé avec succès"
    except Exception as e:
        return False, str(e)

@app.route('/execute-trade', methods=['POST'])
def execute_trade():
    data = request.json or {}
    asset = data.get('asset', 'EURUSD_otc')
    action = data.get('action', 'call')
    amount = float(data.get('amount', 10.0))
    rsi = float(data.get('rsi', 50.0))

    # Durée dynamique / aléatoire selon l'état du marché (RSI)
    if rsi > 70 or rsi < 30:
        duration = random.randint(30, 60)   # Volatilité forte : 30 à 60s
    else:
        duration = random.randint(120, 300) # Volatilité faible : 2 à 5min

    success, msg = send_pocket_order(asset, action, amount, duration)

    if success:
        return jsonify({
            "status": "success",
            "asset": asset,
            "action": action,
            "amount": amount,
            "duration_seconds": duration,
            "message": msg
        }), 200
    else:
        return jsonify({"status": "error", "message": msg}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
  
