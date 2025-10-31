"""
Chat service for managing conversations and learning
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from app.utils.util import get_db_connection


logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat conversations and learning"""
    
    @staticmethod
    def create_tables():
        """Create chat-related tables if they don't exist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Chat conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                context TEXT,
                sentiment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # User preferences learned from interactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                preferred_stocks TEXT,
                interaction_style TEXT,
                topics_of_interest TEXT,
                learning_data TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Agent learning data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_agent_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_type TEXT NOT NULL,
                question_pattern TEXT NOT NULL,
                response_template TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Chat tables created successfully")
    
    @staticmethod
    def save_conversation(
        user_id: int,
        message: str,
        response: str,
        context: Optional[Dict] = None,
        sentiment: Optional[str] = None
    ) -> int:
        """Save a conversation exchange"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        context_json = json.dumps(context) if context else None
        created_at = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO chat_conversations 
            (user_id, message, response, context, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, message, response, context_json, sentiment, created_at))
        
        conversation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return conversation_id
    
    @staticmethod
    def get_conversation_history(user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent conversation history for a user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, message, response, context, sentiment, created_at
            FROM chat_conversations
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            context = json.loads(row[3]) if row[3] else None
            history.append({
                'id': row[0],
                'message': row[1],
                'response': row[2],
                'context': context,
                'sentiment': row[4],
                'created_at': row[5]
            })
        
        return list(reversed(history))  # Return in chronological order
    
    @staticmethod
    def update_user_preferences(
        user_id: int,
        preferred_stocks: Optional[List[str]] = None,
        interaction_style: Optional[str] = None,
        topics_of_interest: Optional[List[str]] = None,
        learning_data: Optional[Dict] = None
    ):
        """Update or create user preferences based on interactions"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if preferences exist
        cursor.execute(
            'SELECT id FROM chat_user_preferences WHERE user_id = ?',
            (user_id,)
        )
        exists = cursor.fetchone()
        
        updated_at = datetime.now().isoformat()
        
        if exists:
            # Update existing preferences - use whitelist for field names
            updates = []
            params = []
            
            # Whitelist of allowed fields to prevent SQL injection
            allowed_fields = {
                'preferred_stocks': preferred_stocks,
                'interaction_style': interaction_style,
                'topics_of_interest': topics_of_interest,
                'learning_data': learning_data
            }
            
            for field_name, value in allowed_fields.items():
                if value is not None:
                    updates.append(f'{field_name} = ?')
                    if field_name in ('preferred_stocks', 'topics_of_interest', 'learning_data'):
                        params.append(json.dumps(value))
                    else:
                        params.append(value)
            
            if updates:
                updates.append('updated_at = ?')
                params.append(updated_at)
                params.append(user_id)
                
                query = f'UPDATE chat_user_preferences SET {", ".join(updates)} WHERE user_id = ?'
                cursor.execute(query, params)
        else:
            # Insert new preferences
            cursor.execute('''
                INSERT INTO chat_user_preferences
                (user_id, preferred_stocks, interaction_style, topics_of_interest, learning_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                json.dumps(preferred_stocks) if preferred_stocks else None,
                interaction_style,
                json.dumps(topics_of_interest) if topics_of_interest else None,
                json.dumps(learning_data) if learning_data else None,
                updated_at
            ))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_user_preferences(user_id: int) -> Optional[Dict]:
        """Get user preferences"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT preferred_stocks, interaction_style, topics_of_interest, learning_data, updated_at
            FROM chat_user_preferences
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'preferred_stocks': json.loads(row[0]) if row[0] else [],
            'interaction_style': row[1],
            'topics_of_interest': json.loads(row[2]) if row[2] else [],
            'learning_data': json.loads(row[3]) if row[3] else {},
            'updated_at': row[4]
        }
    
    @staticmethod
    def save_learning_pattern(
        context_type: str,
        question_pattern: str,
        response_template: str
    ):
        """Save a learned response pattern"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        created_at = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO chat_agent_learning
            (context_type, question_pattern, response_template, created_at)
            VALUES (?, ?, ?, ?)
        ''', (context_type, question_pattern, response_template, created_at))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_pattern_success(pattern_id: int, success: bool):
        """Update success/failure count for a learned pattern"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Safely determine which field to increment
        field = 'success_count' if success else 'failure_count'
        last_used = datetime.now().isoformat()
        
        # Use parameterized query with field selection
        if success:
            cursor.execute('''
                UPDATE chat_agent_learning
                SET success_count = success_count + 1, last_used = ?
                WHERE id = ?
            ''', (last_used, pattern_id))
        else:
            cursor.execute('''
                UPDATE chat_agent_learning
                SET failure_count = failure_count + 1, last_used = ?
                WHERE id = ?
            ''', (last_used, pattern_id))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_best_patterns(context_type: str, limit: int = 5) -> List[Dict]:
        """Get best performing patterns for a context type"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, question_pattern, response_template, success_count, failure_count
            FROM chat_agent_learning
            WHERE context_type = ?
            ORDER BY (success_count * 1.0 / NULLIF(success_count + failure_count, 0)) DESC
            LIMIT ?
        ''', (context_type, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        patterns = []
        for row in rows:
            patterns.append({
                'id': row[0],
                'question_pattern': row[1],
                'response_template': row[2],
                'success_count': row[3],
                'failure_count': row[4]
            })
        
        return patterns
