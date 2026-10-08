import os
import random
import json
import re
import websocket
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SSID = os.environ.get("POCKET_OPTION_SSID")

def clean_asset_name(raw_asset):
    # Extrait ce qui est entre parenthèses si présent : "Or (XAU/USD)" -> "XAU/USD"
    match = re.search(r'\((.*?)\)', raw_asset)
    if match:
        raw_asset = match.group(1)
        
    # Nettoie les caractères spéciaux, espaces et slashs : "XAU/USD" -> "XAUUSD"
    clean = re.sub(r'[^A-Za-z0-9]', '', raw_asset).upper()
    
    # Retire OTC si déjà présent à la fin pour éviter les doublons
    if clean.endswith("OTC"):
        clean = clean[:-3]
        
    # Retourne les variantes possibles demandées par Pocket Option
    return [f"{clean}_otc", f"{clean} OTC", clean]

def send_pocket_order(asset, action, amount, duration):
    ws_url = "wss://api-fin.po.market/socket.io/?EIO=4&transport=websocket"
    possible_assets = clean_asset_name(asset)
    
    direction = "call" if action.lower() in ["call", "buy"] else "put"
    last_error = None

    for target_asset in possible_assets:
        try:
            ws = websocket.create_connection(ws_url, timeout=5)
            ws.send(SSID)
            
            trade_data = {
                "asset": target_asset,
                "amount": float(amount),
                "action": direction,
                "isDemo": 1,
                "requestId": random.randint(100000, 999999),
                "time": int(duration)
            }
            
            trade_msg = f'42["openOrder", {json.dumps(trade_data)}]'
            ws.send(trade_msg)
            ws.close()
            return True, f"Ordre {direction.upper()} exécuté pour {target_asset}"
        except Exception as e:
            last_error = str(e)
            continue
            
    return False, f"Échec d'envoi pour {asset}. Erreur : {last_error}"

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
    
