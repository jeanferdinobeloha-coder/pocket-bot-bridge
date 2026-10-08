import os
import random
import json
import websocket
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Autorise les requêtes provenant de Lovable

SSID = os.environ.get("POCKET_OPTION_SSID")

def format_asset_name(asset):
    # Nettoie le nom de la paire (ex: "AUDUSD" -> "AUDUSD_otc")
    clean_asset = asset.replace("/", "").replace(" ", "").upper()
    if not clean_asset.endswith("_OTC"):
        clean_asset = f"{clean_asset}_otc"
    return clean_asset

def send_pocket_order(asset, action, amount, duration):
    ws_url = "wss://api-fin.po.market/socket.io/?EIO=4&transport=websocket"
    try:
        formatted_asset = format_asset_name(asset)
        ws = websocket.create_connection(ws_url, timeout=10)
        
        # Authentification avec le SSID
        ws.send(SSID)
        
        direction = "call" if action.lower() in ["call", "buy"] else "put"
        trade_msg = f'42["openOrder", {{"asset": "{formatted_asset}", "amount": {amount}, "action": "{direction}", "isDemo": 1, "requestId": {random.randint(100000, 999999)}, "time": {duration}}}]'
        
        ws.send(trade_msg)
        ws.close()
        return True, f"Ordre {direction.upper()} envoyé pour {formatted_asset}"
    except Exception as e:
        return False, str(e)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online"}), 200

@app.route('/execute-trade', methods=['POST'])
def execute_trade():
    try:
        data = request.json or {}
        asset = data.get('asset', 'EURUSD_otc')
        action = data.get('action', 'call')
        amount = float(data.get('amount', 10.0))
        rsi = float(data.get('rsi', 50.0))

        # Ajustement dynamique de la durée selon la volatilité du RSI
        if rsi > 70 or rsi < 30:
            duration = random.randint(30, 60)
        else:
            duration = random.randint(120, 300)

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
            return jsonify({"status": "error", "message": msg}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
