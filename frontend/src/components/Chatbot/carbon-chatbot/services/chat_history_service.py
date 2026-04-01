import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from config import Config

class ChatHistoryService:
    """Enhanced chat history management with proper titles and organization"""
    
    def __init__(self):
        self.db_path = Config.CHAT_HISTORY_DIR / "history.db"
        self.init_database()
        print("💾 ChatHistoryService initialized")
    
    def init_database(self):
        """Initialize chat history database with proper schema"""
        Config.CHAT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create enhanced chat history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                response_time REAL DEFAULT 0.0,
                confidence_score REAL DEFAULT 0.0,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_messages ON chat_messages(session_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_updated ON chat_sessions(updated_at)')
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str, first_message: str) -> str:
        """Create a new chat session with proper title"""
        # Generate meaningful title from first message
        title = self._generate_title(first_message)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO chat_sessions (session_id, title, updated_at, message_count)
                VALUES (?, ?, ?, 0)
            ''', (session_id, title, datetime.now().isoformat()))
            
            conn.commit()
            print(f"📝 Created session: {session_id} - {title}")
            
        except Exception as e:
            print(f"❌ Error creating session: {e}")
        finally:
            conn.close()
        
        return title
    
    def _generate_title(self, message: str) -> str:
        """Generate meaningful title from message"""
        # Clean and truncate message
        clean_message = message.strip()
        
        # Remove common question words for cleaner titles
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'could', 'would', 'should']
        words = clean_message.lower().split()
        
        # Keep important words
        important_words = []
        for word in words:
            if word not in question_words and len(word) > 2:
                important_words.append(word.capitalize())
            if len(important_words) >= 4:  # Limit to 4 important words
                break
        
        if important_words:
            title = ' '.join(important_words)
        else:
            title = clean_message
        
        # Truncate to reasonable length
        if len(title) > 40:
            title = title[:37] + "..."
        
        return title or "New Chat"
    
    def add_message(self, session_id: str, role: str, content: str, sources: List[Dict] = None, 
                   response_time: float = 0.0, confidence_score: float = 0.0):
        """Add message to chat history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if session exists, if not create it
            cursor.execute('SELECT session_id FROM chat_sessions WHERE session_id = ?', (session_id,))
            session_exists = cursor.fetchone()
            
            if not session_exists:
                # Create session automatically with first message as title
                title = self._generate_title(content) if role == 'user' else "New Chat"
                cursor.execute('''
                    INSERT INTO chat_sessions (session_id, title, updated_at, message_count)
                    VALUES (?, ?, ?, 0)
                ''', (session_id, title, datetime.now().isoformat()))
                print(f"📝 Auto-created session: {session_id} - {title}")
            
            # Add message
            cursor.execute('''
                INSERT INTO chat_messages (session_id, message_role, content, sources, response_time, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, role, content, json.dumps(sources) if sources else None, response_time, confidence_score))
            
            # Update session
            cursor.execute('''
                UPDATE chat_sessions 
                SET updated_at = ?, message_count = message_count + 1
                WHERE session_id = ?
            ''', (datetime.now().isoformat(), session_id))
            
            # If this is the first user message, update title
            if role == 'user':
                cursor.execute('SELECT COUNT(*) FROM chat_messages WHERE session_id = ? AND message_role = ?', (session_id, 'user'))
                user_message_count = cursor.fetchone()[0]
                
                if user_message_count == 1:  # First user message
                    title = self._generate_title(content)
                    cursor.execute('UPDATE chat_sessions SET title = ? WHERE session_id = ?', (title, session_id))
                    print(f"📝 Updated session title: {session_id} - {title}")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error adding message: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
    
    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT message_role, content, sources, timestamp, response_time, confidence_score
                FROM chat_messages 
                WHERE session_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (session_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                role, content, sources, timestamp, response_time, confidence_score = row
                
                message = {
                    "role": role,
                    "content": content,
                    "timestamp": timestamp,
                    "response_time": response_time,
                    "confidence_score": confidence_score
                }
                
                if sources:
                    try:
                        message["sources"] = json.loads(sources)
                    except:
                        message["sources"] = []
                
                messages.append(message)
            
            return list(reversed(messages))  # Return in chronological order
            
        except Exception as e:
            print(f"❌ Error getting session history: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of all chat sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT session_id, title, created_at, updated_at, message_count
                FROM chat_sessions 
                ORDER BY updated_at DESC 
                LIMIT ?
            ''', (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                session_id, title, created_at, updated_at, message_count = row
                
                sessions.append({
                    "session_id": session_id,
                    "title": title,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "message_count": message_count
                })
            
            return sessions
            
        except Exception as e:
            print(f"❌ Error getting sessions: {e}")
            return []
        finally:
            conn.close()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session and all its messages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM chat_sessions WHERE session_id = ?', (session_id,))
            
            conn.commit()
            print(f"🗑️ Deleted session: {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting session: {e}")
            return False
        finally:
            conn.close()

# Global instance
_chat_history_service = None

def get_chat_history_service() -> ChatHistoryService:
    """Get global chat history service instance"""
    global _chat_history_service
    if _chat_history_service is None:
        _chat_history_service = ChatHistoryService()
    return _chat_history_service