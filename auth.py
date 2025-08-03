#!/usr/bin/env python3
"""
Authentication module for the AI Chatbot
Handles user registration, login, and session management
"""

import bcrypt
import hashlib
import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash

# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "chatbot.db")

class AuthManager:
    """Manages user authentication and authorization"""
    
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_auth_tables()
    
    def init_auth_tables(self):
        """Initialize authentication tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create users_auth table for authentication
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users_auth (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Create user_profiles table for additional user info
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        display_name TEXT,
                        avatar_url TEXT,
                        preferences TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users_auth (id)
                    )
                ''')
                
                conn.commit()
                print("✅ Authentication tables initialized")
                
        except Exception as e:
            print(f"❌ Error initializing auth tables: {e}")
    
    def hash_password(self, password):
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)
    
    def verify_password(self, password, password_hash):
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def verify_legacy_password(self, password, password_hash):
        """Verify a password against legacy SHA-256 hash"""
        try:
            legacy_hash = hashlib.sha256(password.encode()).hexdigest()
            return legacy_hash == password_hash
        except Exception:
            return False
    
    def migrate_password(self, user_id, password):
        """Migrate a user's password from SHA-256 to bcrypt"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Hash with bcrypt
                new_hash = self.hash_password(password)
                
                # Update the password hash
                cursor.execute('''
                    UPDATE users_auth SET password_hash = ? WHERE id = ?
                ''', (new_hash.decode('utf-8'), user_id))
                
                conn.commit()
                print(f"✅ Migrated password for user {user_id}")
                return True
                
        except Exception as e:
            print(f"❌ Error migrating password: {e}")
            return False
    
    def register_user(self, username, email, password):
        """Register a new user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if username or email already exists
                cursor.execute('''
                    SELECT id FROM users_auth 
                    WHERE username = ? OR email = ?
                ''', (username, email))
                
                if cursor.fetchone():
                    return False, "Username or email already exists"
                
                # Hash password and create user
                password_hash = self.hash_password(password)
                # Convert bytes to string for database storage
                password_hash_str = password_hash.decode('utf-8')
                
                cursor.execute('''
                    INSERT INTO users_auth (username, email, password_hash)
                    VALUES (?, ?, ?)
                ''', (username, email, password_hash_str))
                
                user_id = cursor.lastrowid
                
                # Create user profile
                cursor.execute('''
                    INSERT INTO user_profiles (user_id, display_name)
                    VALUES (?, ?)
                ''', (user_id, username))
                
                conn.commit()
                return True, f"User {username} registered successfully"
                
        except Exception as e:
            print(f"❌ Error registering user: {e}")
            return False, "Registration failed"
    
    def login_user(self, username, password):
        """Authenticate a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, password_hash FROM users_auth 
                    WHERE username = ? AND is_active = 1
                ''', (username,))
                
                user = cursor.fetchone()
                
                if user:
                    user_id, username, password_hash = user
                    print(f"🔍 Attempting login for user: {username}")
                    
                    # Try bcrypt verification first
                    if self.verify_password(password, password_hash):
                        print(f"✅ Bcrypt verification successful for user: {username}")
                        # Update last login
                        cursor.execute('''
                            UPDATE users_auth SET last_login = datetime('now')
                            WHERE id = ?
                        ''', (user_id,))
                        
                        conn.commit()
                        return True, user_id, username
                    
                    # If bcrypt fails, try legacy SHA-256 verification
                    elif self.verify_legacy_password(password, password_hash):
                        print(f"✅ Legacy SHA-256 verification successful for user: {username}")
                        # Migrate password to bcrypt
                        if self.migrate_password(user_id, password):
                            # Update last login
                            cursor.execute('''
                                UPDATE users_auth SET last_login = datetime('now')
                                WHERE id = ?
                            ''', (user_id,))
                            
                            conn.commit()
                            return True, user_id, username
                    else:
                        print(f"❌ Password verification failed for user: {username}")
                else:
                    print(f"❌ User not found: {username}")
                
                return False, None, None
                    
        except Exception as e:
            print(f"❌ Error during login: {e}")
            return False, None, None
    
    def get_user_by_id(self, user_id):
        """Get user information by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT ua.id, ua.username, ua.email, ua.created_at, ua.last_login,
                           up.display_name, up.avatar_url, up.preferences
                    FROM users_auth ua
                    LEFT JOIN user_profiles up ON ua.id = up.user_id
                    WHERE ua.id = ? AND ua.is_active = 1
                ''', (user_id,))
                
                user = cursor.fetchone()
                if user:
                    return {
                        'id': user[0],
                        'username': user[1],
                        'email': user[2],
                        'created_at': user[3],
                        'last_login': user[4],
                        'display_name': user[5],
                        'avatar_url': user[6],
                        'preferences': user[7]
                    }
                return None
                
        except Exception as e:
            print(f"❌ Error getting user: {e}")
            return None
    
    def update_user_profile(self, user_id, display_name=None, avatar_url=None, preferences=None):
        """Update user profile information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if display_name or avatar_url or preferences:
                    cursor.execute('''
                        UPDATE user_profiles 
                        SET display_name = COALESCE(?, display_name),
                            avatar_url = COALESCE(?, avatar_url),
                            preferences = COALESCE(?, preferences),
                            updated_at = datetime('now')
                        WHERE user_id = ?
                    ''', (display_name, avatar_url, preferences, user_id))
                    
                    conn.commit()
                    return True
                return False
                
        except Exception as e:
            print(f"❌ Error updating profile: {e}")
            return False
    
    def change_password(self, user_id, old_password, new_password):
        """Change user password"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current password hash
                cursor.execute('''
                    SELECT password_hash FROM users_auth WHERE id = ?
                ''', (user_id,))
                
                current_hash = cursor.fetchone()
                if not current_hash:
                    return False, "User not found"
                
                # Verify old password
                if not self.verify_password(old_password, current_hash[0]):
                    return False, "Current password is incorrect"
                
                # Update password
                new_hash = self.hash_password(new_password)
                cursor.execute('''
                    UPDATE users_auth SET password_hash = ? WHERE id = ?
                ''', (new_hash, user_id))
                
                conn.commit()
                return True, "Password changed successfully"
                
        except Exception as e:
            print(f"❌ Error changing password: {e}")
            return False, "Failed to change password"

# Initialize auth manager
auth_manager = AuthManager()

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current user information"""
    if 'user_id' in session:
        user_id = session['user_id']
        
        # Handle prefixed user IDs (auth_user_123)
        if isinstance(user_id, str) and user_id.startswith('auth_user_'):
            actual_user_id = int(user_id.replace('auth_user_', ''))
            return auth_manager.get_user_by_id(actual_user_id)
        elif isinstance(user_id, int):
            # Legacy case: direct integer user ID
            return auth_manager.get_user_by_id(user_id)
    
    return None 