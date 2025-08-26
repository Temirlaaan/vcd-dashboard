# history_service.py - Сервис для работы с историей и заметками
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import sqlite3
from contextlib import contextmanager

from models_extended import HistoryEntry, Note, ActionType

class HistoryService:
    """Сервис для работы с историей операций и заметками"""
    
    def __init__(self, db_path: str = "vcd_history.db"):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def get_db(self):
        """Контекстный менеджер для работы с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Инициализация базы данных"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            
            # Таблица истории
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action_type TEXT NOT NULL,
                    user TEXT NOT NULL,
                    ip_address TEXT,
                    cloud_name TEXT,
                    pool_name TEXT,
                    organization TEXT,
                    details TEXT,
                    old_value TEXT,
                    new_value TEXT
                )
            ''')
            
            # Таблица заметок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    author TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    priority TEXT DEFAULT 'medium',
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    ip_address TEXT,
                    cloud_name TEXT,
                    pool_name TEXT,
                    tags TEXT,
                    is_pinned INTEGER DEFAULT 0,
                    expires_at DATETIME
                )
            ''')
            
            # Индексы для быстрого поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_ip ON history(ip_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_user ON history(user)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author)')
            
            conn.commit()
    
    def add_history_entry(
        self,
        action_type: ActionType,
        user: str,
        ip_address: Optional[str] = None,
        cloud_name: Optional[str] = None,
        pool_name: Optional[str] = None,
        organization: Optional[str] = None,
        details: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None
    ) -> int:
        """Добавить запись в историю"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO history (
                    action_type, user, ip_address, cloud_name, 
                    pool_name, organization, details, old_value, new_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                action_type, user, ip_address, cloud_name,
                pool_name, organization, details, old_value, new_value
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_history(
        self,
        limit: int = 100,
        offset: int = 0,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        action_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[dict]:
        """Получить историю с фильтрами"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM history WHERE 1=1"
            params = []
            
            if user:
                query += " AND user = ?"
                params.append(user)
            
            if ip_address:
                query += " AND ip_address = ?"
                params.append(ip_address)
            
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)
            
            if date_from:
                query += " AND timestamp >= ?"
                params.append(date_from.isoformat())
            
            if date_to:
                query += " AND timestamp <= ?"
                params.append(date_to.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_note(
        self,
        author: str,
        title: str,
        content: str,
        category: str = "general",
        priority: str = "medium",
        ip_address: Optional[str] = None,
        cloud_name: Optional[str] = None,
        pool_name: Optional[str] = None,
        tags: List[str] = None,
        is_pinned: bool = False,
        expires_at: Optional[datetime] = None
    ) -> int:
        """Добавить заметку"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notes (
                    author, title, content, category, priority,
                    ip_address, cloud_name, pool_name, tags, is_pinned, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                author, title, content, category, priority,
                ip_address, cloud_name, pool_name,
                json.dumps(tags or []), int(is_pinned),
                expires_at.isoformat() if expires_at else None
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_notes(
        self,
        limit: int = 50,
        offset: int = 0,
        author: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        ip_address: Optional[str] = None,
        include_expired: bool = False
    ) -> List[dict]:
        """Получить заметки с фильтрами"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM notes WHERE 1=1"
            params = []
            
            if author:
                query += " AND author = ?"
                params.append(author)
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if priority:
                query += " AND priority = ?"
                params.append(priority)
            
            if ip_address:
                query += " AND ip_address = ?"
                params.append(ip_address)
            
            if not include_expired:
                query += " AND (expires_at IS NULL OR expires_at > ?)"
                params.append(datetime.now().isoformat())
            
            query += " ORDER BY is_pinned DESC, created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            notes = []
            for row in cursor.fetchall():
                note = dict(row)
                note['tags'] = json.loads(note.get('tags', '[]'))
                note['is_pinned'] = bool(note.get('is_pinned', 0))
                notes.append(note)
            
            return notes
    
    def update_note(self, note_id: int, **kwargs) -> bool:
        """Обновить заметку"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            
            set_clause = []
            params = []
            
            for key, value in kwargs.items():
                if key == 'tags':
                    value = json.dumps(value)
                elif key == 'is_pinned':
                    value = int(value)
                elif key == 'expires_at' and value:
                    value = value.isoformat()
                
                set_clause.append(f"{key} = ?")
                params.append(value)
            
            if not set_clause:
                return False
            
            set_clause.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            
            params.append(note_id)
            
            query = f"UPDATE notes SET {', '.join(set_clause)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def delete_note(self, note_id: int) -> bool:
        """Удалить заметку"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def cleanup_old_entries(self, days: int = 90):
        """Очистка старых записей истории"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM history WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            
            # Удаляем истекшие заметки
            cursor.execute(
                "DELETE FROM notes WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.now().isoformat(),)
            )
            
            conn.commit()
            return cursor.rowcount
    
    def get_statistics(self) -> dict:
        """Получить статистику по истории и заметкам"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            
            # Статистика по истории
            cursor.execute("SELECT COUNT(*) as total FROM history")
            total_history = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT action_type, COUNT(*) as count 
                FROM history 
                GROUP BY action_type
            """)
            history_by_type = {row['action_type']: row['count'] for row in cursor.fetchall()}
            
            cursor.execute("""
                SELECT user, COUNT(*) as count 
                FROM history 
                GROUP BY user 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_users = [dict(row) for row in cursor.fetchall()]
            
            # Статистика по заметкам
            cursor.execute("SELECT COUNT(*) as total FROM notes")
            total_notes = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as pinned FROM notes WHERE is_pinned = 1")
            pinned_notes = cursor.fetchone()['pinned']
            
            return {
                'history': {
                    'total': total_history,
                    'by_type': history_by_type,
                    'top_users': top_users
                },
                'notes': {
                    'total': total_notes,
                    'pinned': pinned_notes
                }
            }

# Глобальный экземпляр сервиса
history_service = HistoryService()