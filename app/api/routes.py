# Placeholder for API routes

from fastapi import APIRouter, HTTPException
from app.api.config_routes import router as config_router
from app.models.training_script import train_transformer_model, train_model
from app.services.configuration_service import ConfigurationService
from typing import Optional
from pydantic import BaseModel
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.db_executor import get_db_connection, fetch_one, fetch_all
from datetime import datetime

router = APIRouter()
api = Blueprint('api', __name__)

# Include configuration routes
router.include_router(config_router, tags=["configurations"])

class TrainingResponse(BaseModel):
    symbol: str
    model_type: str
    model_path: str
    metrics: dict

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.post("/train/{symbol}", response_model=TrainingResponse)
async def train_stock_model(symbol: str, model_type: str = "transformer"):
    """Train a model for a specific stock symbol using stored configurations"""
    try:
        # Get configuration for the symbol
        config = ConfigurationService.get_configuration(symbol, model_type)

        if model_type == "transformer":
            model, scaler = train_transformer_model(
                symbol,
                time_step=config.sequence_length if config else 60,
                epochs=config.epochs if config else 100,
                batch_size=config.batch_size if config else 32
            )
        else:
            model, scaler = train_model(symbol)

        # The model saving is handled within the training functions
        # Return the training results
        return {
            "symbol": symbol,
            "model_type": model_type,
            "model_path": f"model/saved_models/{symbol}_{model_type}_latest",
            "metrics": {
                "status": "success",
                "configuration_used": config is not None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if not username or not password or not email:
        return jsonify({'error': 'Missing required fields'}), 400
    password_hash = generate_password_hash(password)
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    try:
        # Check for existing username/email
        existing_user = fetch_one('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        if existing_user:
            return jsonify({'error': 'Username or email already exists'}), 400
        conn.execute('INSERT INTO users (username, password_hash, email, created_at) VALUES (?, ?, ?, ?)',
                     (username, password_hash, email, created_at))
        conn.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        print(f"Registration error: {e}")  # Debug output
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    user = fetch_one('SELECT * FROM users WHERE username = ?', (username,))
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@api.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@api.route('/account', methods=['GET'])
def account_info():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    user = fetch_one('SELECT id, username, email, created_at FROM users WHERE id = ?', (user_id,))
    return jsonify(user), 200

@api.route('/watchlist', methods=['GET', 'POST', 'DELETE'])
def watchlist():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    conn = get_db_connection()
    if request.method == 'GET':
        watchlist = fetch_all('SELECT security_id FROM user_watchlist WHERE user_id = ?', (user_id,))
        return jsonify({'watchlist': [w['security_id'] for w in watchlist]}), 200
    elif request.method == 'POST':
        data = request.get_json()
        security_id = data.get('security_id')
        if not security_id:
            return jsonify({'error': 'Missing security_id'}), 400
        added_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            conn.execute('INSERT INTO user_watchlist (user_id, security_id, added_at) VALUES (?, ?, ?)',
                         (user_id, security_id, added_at))
            conn.commit()
            return jsonify({'message': 'Stock added to watchlist'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    elif request.method == 'DELETE':
        data = request.get_json()
        security_id = data.get('security_id')
        if not security_id:
            return jsonify({'error': 'Missing security_id'}), 400
        try:
            conn.execute('DELETE FROM user_watchlist WHERE user_id = ? AND security_id = ?',
                         (user_id, security_id))
            conn.commit()
            return jsonify({'message': 'Stock removed from watchlist'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    conn.close()
