"""Session Manager Service - Manages chat sessions and their metadata"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from config import Config

class SessionManager:
    """Manages chat sessions, files, and session metadata"""
    
    def __init__(self):
        self.db_path = Config.CHAT_HISTORY_DIR / "sessions.db"
        self.init_database()
        print("📋 SessionManager initialized")
    
    def init_database(self):
        """Initialize session database"""
        Config.CHAT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Session files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                relevance_score REAL DEFAULT 0.0,
                processing_status TEXT DEFAULT 'pending',
                chunks_processed INTEGER DEFAULT 0,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')
        
        # Add status columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE session_files ADD COLUMN processing_status TEXT DEFAULT "pending"')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE session_files ADD COLUMN chunks_processed INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Session messages table (lightweight, for quick access)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_new_session(self, first_message: str = "") -> str:
        """Create a new session"""
        session_id = f"session_{int(datetime.now().timestamp() * 1000)}"
        title = self._generate_title(first_message) if first_message else "New Chat"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO sessions (session_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (session_id, title, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            print(f"✅ Created new session: {session_id}")
            
        except Exception as e:
            print(f"❌ Error creating session: {e}")
        finally:
            conn.close()
        
        return session_id
    
    def _generate_title(self, message: str) -> str:
        """Generate title from message"""
        clean_message = message.strip()
        if len(clean_message) > 40:
            return clean_message[:37] + "..."
        return clean_message or "New Chat"
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM sessions WHERE session_id = ?', (session_id,))
            count = cursor.fetchone()[0]
            return count > 0
        except:
            return False
        finally:
            conn.close()
    
    def add_session_file(self, session_id: str, filename: str, filepath: str, relevance_score: float = 0.0):
        """Add a file to a session"""
        # Ensure session exists
        if not self.session_exists(session_id):
            self.create_new_session(f"File upload: {filename}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO session_files (session_id, filename, filepath, relevance_score)
                VALUES (?, ?, ?, ?)
            ''', (session_id, filename, filepath, relevance_score))
            
            # Update session timestamp
            cursor.execute('''
                UPDATE sessions SET updated_at = ? WHERE session_id = ?
            ''', (datetime.now().isoformat(), session_id))
            
            conn.commit()
            print(f"📎 Added file to session {session_id}: {filename}")
            
        except Exception as e:
            print(f"❌ Error adding file to session: {e}")
        finally:
            conn.close()
    
    def get_session_files(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all files for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT filename, filepath, relevance_score, uploaded_at, processing_status, chunks_processed
                FROM session_files
                WHERE session_id = ?
                ORDER BY uploaded_at DESC
            ''', (session_id,))
            
            files = []
            for row in cursor.fetchall():
                filename, filepath, relevance_score, uploaded_at, processing_status, chunks_processed = row
                files.append({
                    "filename": filename,
                    "filepath": filepath,
                    "relevance_score": relevance_score,
                    "uploaded_at": uploaded_at,
                    "processing_status": processing_status or 'pending',
                    "chunks_processed": chunks_processed or 0
                })
            
            return files
            
        except Exception as e:
            print(f"❌ Error getting session files: {e}")
            return []
        finally:
            conn.close()
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to session (lightweight tracking)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO session_messages (session_id, role, content)
                VALUES (?, ?, ?)
            ''', (session_id, role, content))
            
            # Update session timestamp
            cursor.execute('''
                UPDATE sessions SET updated_at = ? WHERE session_id = ?
            ''', (datetime.now().isoformat(), session_id))
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error adding message: {e}")
        finally:
            conn.close()
    
    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get session message history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT role, content, timestamp
                FROM session_messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (session_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                role, content, timestamp = row
                messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": timestamp
                })
            
            return list(reversed(messages))
            
        except Exception as e:
            print(f"❌ Error getting session history: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all sessions with metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT s.session_id, s.title, s.created_at, s.updated_at,
                       (SELECT COUNT(*) FROM session_messages WHERE session_id = s.session_id) as message_count,
                       (SELECT content FROM session_messages WHERE session_id = s.session_id AND role = 'user' ORDER BY timestamp ASC LIMIT 1) as first_message
                FROM sessions s
                ORDER BY s.updated_at DESC
                LIMIT ?
            ''', (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                session_id, title, created_at, updated_at, message_count, first_message = row
                
                sessions.append({
                    "session_id": session_id,
                    "title": title or first_message or "New Chat",
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "message_count": message_count,
                    "first_message": first_message
                })
            
            return sessions
            
        except Exception as e:
            print(f"❌ Error getting all sessions: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            conn.close()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM session_files WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM session_messages WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            
            conn.commit()
            print(f"🗑️ Deleted session: {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting session: {e}")
            return False
        finally:
            conn.close()
    
    def update_file_processing_status(self, session_id: str, filename: str, status: str, chunks_processed: int = 0):
        """Update the processing status of a file in a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE session_files 
                SET processing_status = ?, chunks_processed = ?
                WHERE session_id = ? AND filename = ?
            ''', (status, chunks_processed, session_id, filename))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f"📎 Updated file status: {filename} -> {status} ({chunks_processed} chunks)")
            
        except Exception as e:
            print(f"❌ Error updating file status: {e}")
        finally:
            conn.close()

# Global instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
