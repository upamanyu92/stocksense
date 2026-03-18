"""
Chat service for managing conversations and learning
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from app.db.session_manager import get_session_manager


logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat conversations and learning"""
    
    @staticmethod
    def create_tables():
        """Create chat-related tables if they don't exist"""
        db = get_session_manager()

        # Chat conversations table
        db.execute('''
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
        ''', commit=True)

        # User preferences learned from interactions
        db.execute('''
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
        ''', commit=True)

        # Agent learning data
        db.execute('''
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
        ''', commit=True)

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
        db = get_session_manager()

        context_json = json.dumps(context) if context else None
        created_at = datetime.now().isoformat()
        
        conversation_id = db.insert('''
            INSERT INTO chat_conversations 
            (user_id, message, response, context, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, message, response, context_json, sentiment, created_at))
        
        return conversation_id or -1

    @staticmethod
    def get_conversation_history(user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent conversation history for a user"""
        db = get_session_manager()

        rows = db.fetch_all('''
            SELECT id, message, response, context, sentiment, created_at
            FROM chat_conversations
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        history = []
        for row in rows:
            context = json.loads(row['context']) if row['context'] else None
            history.append({
                'id': row['id'],
                'message': row['message'],
                'response': row['response'],
                'context': context,
                'sentiment': row['sentiment'],
                'created_at': row['created_at']
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
        db = get_session_manager()

        # Check if preferences exist
        exists = db.fetch_one(
            'SELECT id FROM chat_user_preferences WHERE user_id = ?',
            (user_id,)
        )

        updated_at = datetime.now().isoformat()
        
        if exists:
            # Update existing preferences - use explicit field names to prevent SQL injection
            params = []
            update_clauses = []
            
            # Only update fields that are provided (not None)
            if preferred_stocks is not None:
                update_clauses.append('preferred_stocks = ?')
                params.append(json.dumps(preferred_stocks))
            if interaction_style is not None:
                update_clauses.append('interaction_style = ?')
                params.append(interaction_style)
            if topics_of_interest is not None:
                update_clauses.append('topics_of_interest = ?')
                params.append(json.dumps(topics_of_interest))
            if learning_data is not None:
                update_clauses.append('learning_data = ?')
                params.append(json.dumps(learning_data))
            
            if update_clauses:
                # Add updated_at timestamp
                update_clauses.append('updated_at = ?')
                params.append(updated_at)
                params.append(user_id)
                
                # Use explicit field names - safe from SQL injection
                query = 'UPDATE chat_user_preferences SET ' + ', '.join(update_clauses) + ' WHERE user_id = ?'
                db.update(query, tuple(params))
        else:
            # Insert new preferences
            db.insert('''
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

    @staticmethod
    def get_user_preferences(user_id: int) -> Optional[Dict]:
        """Get user preferences"""
        db = get_session_manager()

        row = db.fetch_one('''
            SELECT preferred_stocks, interaction_style, topics_of_interest, learning_data, updated_at
            FROM chat_user_preferences
            WHERE user_id = ?
        ''', (user_id,))
        
        if not row:
            return None
        
        return {
            'preferred_stocks': json.loads(row['preferred_stocks']) if row['preferred_stocks'] else [],
            'interaction_style': row['interaction_style'],
            'topics_of_interest': json.loads(row['topics_of_interest']) if row['topics_of_interest'] else [],
            'learning_data': json.loads(row['learning_data']) if row['learning_data'] else {},
            'updated_at': row['updated_at']
        }
    
    @staticmethod
    def save_learning_pattern(
        context_type: str,
        question_pattern: str,
        response_template: str
    ):
        """Save a learned response pattern"""
        db = get_session_manager()

        created_at = datetime.now().isoformat()
        
        db.insert('''
            INSERT INTO chat_agent_learning
            (context_type, question_pattern, response_template, created_at)
            VALUES (?, ?, ?, ?)
        ''', (context_type, question_pattern, response_template, created_at))

    @staticmethod
    def update_pattern_success(pattern_id: int, success: bool):
        """Update success/failure count for a learned pattern"""
        db = get_session_manager()

        last_used = datetime.now().isoformat()
        
        # Use parameterized query with field selection
        if success:
            db.update('''
                UPDATE chat_agent_learning
                SET success_count = success_count + 1, last_used = ?
                WHERE id = ?
            ''', (last_used, pattern_id))
        else:
            db.update('''
                UPDATE chat_agent_learning
                SET failure_count = failure_count + 1, last_used = ?
                WHERE id = ?
            ''', (last_used, pattern_id))

    @staticmethod
    def get_best_patterns(context_type: str, limit: int = 5) -> List[Dict]:
        """Get best performing patterns for a context type"""
        db = get_session_manager()

        rows = db.fetch_all('''
            SELECT id, question_pattern, response_template, success_count, failure_count
            FROM chat_agent_learning
            WHERE context_type = ?
            ORDER BY (success_count * 1.0 / NULLIF(success_count + failure_count, 0)) DESC
            LIMIT ?
        ''', (context_type, limit))
        
        patterns = []
        for row in rows:
            patterns.append({
                'id': row['id'],
                'question_pattern': row['question_pattern'],
                'response_template': row['response_template'],
                'success_count': row['success_count'],
                'failure_count': row['failure_count']
            })
        
        return patterns


