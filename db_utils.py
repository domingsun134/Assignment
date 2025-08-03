#!/usr/bin/env python3
"""
Database utility script for the AI Chatbot
Provides functions for database backup, restore, and maintenance.
"""

import sqlite3
import os
import shutil
import json
from datetime import datetime
import argparse

DATABASE_PATH = os.getenv("DATABASE_PATH", "chatbot.db")

def backup_database(backup_path=None):
    """Create a backup of the database"""
    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_chatbot_{timestamp}.db"
    
    try:
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, backup_path)
            print(f"✅ Database backed up to: {backup_path}")
            return True
        else:
            print("❌ Database file not found")
            return False
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def restore_database(backup_path):
    """Restore database from backup"""
    try:
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, DATABASE_PATH)
            print(f"✅ Database restored from: {backup_path}")
            return True
        else:
            print("❌ Backup file not found")
            return False
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

def get_database_stats():
    """Get database statistics"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Get user count
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # Get conversation count
            cursor.execute("SELECT COUNT(*) FROM conversations")
            conversation_count = cursor.fetchone()[0]
            
            # Get message count
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            
            # Get recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_active > datetime('now', '-7 days')
            """)
            active_users = cursor.fetchone()[0]
            
            print("📊 Database Statistics:")
            print(f"   Users: {user_count}")
            print(f"   Conversations: {conversation_count}")
            print(f"   Messages: {message_count}")
            print(f"   Active users (7 days): {active_users}")
            
            return {
                'users': user_count,
                'conversations': conversation_count,
                'messages': message_count,
                'active_users': active_users
            }
    except Exception as e:
        print(f"❌ Error getting database stats: {e}")
        return None

def export_user_data(user_id, output_file=None):
    """Export user data to JSON"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Get user info
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ User {user_id} not found")
                return False
            
            # Get user conversations
            cursor.execute("""
                SELECT conversation_id, title, model, created_at, updated_at
                FROM conversations WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))
            conversations = cursor.fetchall()
            
            # Get messages for each conversation
            user_data = {
                'user_id': user[1],
                'username': user[2],
                'created_at': user[3],
                'last_active': user[4],
                'conversations': []
            }
            
            for conv in conversations:
                conversation_data = {
                    'conversation_id': conv[0],
                    'title': conv[1],
                    'model': conv[2],
                    'created_at': conv[3],
                    'updated_at': conv[4],
                    'messages': []
                }
                
                # Get messages for this conversation
                cursor.execute("""
                    SELECT role, content, model, timestamp
                    FROM messages WHERE conversation_id = ?
                    ORDER BY timestamp ASC
                """, (conv[0],))
                
                messages = cursor.fetchall()
                for msg in messages:
                    conversation_data['messages'].append({
                        'role': msg[0],
                        'content': msg[1],
                        'model': msg[2],
                        'timestamp': msg[3]
                    })
                
                user_data['conversations'].append(conversation_data)
            
            if not output_file:
                output_file = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ User data exported to: {output_file}")
            return True
            
    except Exception as e:
        print(f"❌ Error exporting user data: {e}")
        return False

def cleanup_old_data(days=30):
    """Clean up old data (users inactive for specified days)"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Get inactive users
            cursor.execute("""
                SELECT user_id FROM users 
                WHERE last_active < datetime('now', '-{} days')
            """.format(days))
            
            inactive_users = cursor.fetchall()
            
            if not inactive_users:
                print(f"✅ No users inactive for {days} days")
                return True
            
            print(f"🗑️  Found {len(inactive_users)} inactive users")
            
            for user in inactive_users:
                user_id = user[0]
                print(f"   Deleting user: {user_id}")
                
                # Delete user conversations and messages
                cursor.execute("SELECT conversation_id FROM conversations WHERE user_id = ?", (user_id,))
                conversation_ids = [row[0] for row in cursor.fetchall()]
                
                for conv_id in conversation_ids:
                    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
                
                cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            
            conn.commit()
            print(f"✅ Cleaned up {len(inactive_users)} inactive users")
            return True
            
    except Exception as e:
        print(f"❌ Error cleaning up old data: {e}")
        return False

def main():
    """Main function for command line interface"""
    parser = argparse.ArgumentParser(description="Database utility for AI Chatbot")
    parser.add_argument('action', choices=['backup', 'restore', 'stats', 'export', 'cleanup'],
                       help='Action to perform')
    parser.add_argument('--file', help='File path for backup/restore/export')
    parser.add_argument('--user-id', help='User ID for export')
    parser.add_argument('--days', type=int, default=30, help='Days for cleanup (default: 30)')
    
    args = parser.parse_args()
    
    if args.action == 'backup':
        backup_database(args.file)
    elif args.action == 'restore':
        if not args.file:
            print("❌ Please specify backup file with --file")
            return
        restore_database(args.file)
    elif args.action == 'stats':
        get_database_stats()
    elif args.action == 'export':
        if not args.user_id:
            print("❌ Please specify user ID with --user-id")
            return
        export_user_data(args.user_id, args.file)
    elif args.action == 'cleanup':
        cleanup_old_data(args.days)

if __name__ == '__main__':
    main() 