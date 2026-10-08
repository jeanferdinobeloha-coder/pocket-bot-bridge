import os
import random
import json
import re
import websocket
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SESSION_TOKEN = os.environ.get("POCKET_OPTION_SSID", "").strip()

def clean_asset_name(raw_asset):
    match = re.search(r'\((.*?)\)', raw_asset)
    if match:
        raw_asset = match.group(1)
        
    clean = re.sub(r'[^A-Za-z0-9]', '', raw_asset).upper()
    if clean.endswith("OTC"):
        clean = clean[:-3]
        
    return [f"{clean}_otc", clean, f"{clean} OTC"]

def send_pocket_order(asset, action, amount, duration):
    ws_url = "wss://api-fin.po.market/socket.io/?EIO=4&transport=websocket"
    possible_assets = clean_asset_name(asset)
    direction = "call" if action.lower() in ["call", "buy"] else "put"
    last_error = None

    for target_asset in possible_assets:
        try:
            ws = websocket.create_connection(ws_url, timeout=8)
            
            # 1. Message d'authentification
            auth_payload = {
                "session": SESSION_TOKEN,
                "isDemo": 1
            }
            ws.send(f'42["auth", {json.dumps(auth_payload)}]')
            
            # Attente de la confirmation
            try:
                ws.recv()
            except Exception:
                pass

            # 2. Envoi de la commande d'ouverture de position
            trade_payload = {
                "asset": target_asset,
                "amount": float(amount),
                "action": direction,
                "isDemo": 1,
                "requestId": random.randint(100000, 999999),
                "time": int(duration)
            }
            
            ws.send(f'42["openOrder", {json.dumps(trade_payload)}]')
            ws.close()
            return True, f"Ordre {direction.upper()} envoyé avec succès pour {target_asset}"
        except Exception as e:
            last_error = str(e)
            continue
            
    return False, f"Échec pour {asset}. Erreur : {last_error}"

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

        duration = random.randint(30, 60) if (rsi > 70 or rsi < 30) else random.randint(120, 300)

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
