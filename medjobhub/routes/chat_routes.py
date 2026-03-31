from flask import request, jsonify, session, send_from_directory
from flask_socketio import emit, join_room, leave_room
from medjobhub import app, db, socketio
from medjobhub.models import ChatMessage, User
from datetime import datetime
import json
import os

active_users = {}

@app.route('/api/chat/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for the current user"""
    try:
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "User not authenticated"}), 401
        
        user_id = session['user_id']
        
        # Get all unique conversations where user is sender or receiver
        conversations = db.session.query(ChatMessage).filter(
            db.or_(
                ChatMessage.sender_id == user_id,
                ChatMessage.receiver_id == user_id
            )
        ).order_by(ChatMessage.timestamp.desc()).all()
        
        conversation_dict = {}
        for msg in conversations:
            partner_id = msg.receiver_id if msg.sender_id == user_id else msg.sender_id
            
            if partner_id not in conversation_dict:
                partner = User.query.get(partner_id)
                if partner:
                    conversation_dict[partner_id] = {
                        'partner_id': partner_id,
                        'partner_name': f"{partner.first_name} {partner.last_name}",
                        'partner_role': partner.role,
                        'partner_company': partner.company_name if partner.role == 'employer' else None,
                        'last_message': msg.message,
                        'last_timestamp': msg.timestamp.isoformat(),
                        'room': msg.room
                    }
        
        conversations_list = list(conversation_dict.values())
        return jsonify({"success": True, "conversations": conversations_list})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/chat/messages/<int:partner_id>', methods=['GET'])
def get_chat_messages(partner_id):
    """Get chat messages between current user and partner"""
    try:
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "User not authenticated"}), 401
        
        user_id = session['user_id']
        
        messages = ChatMessage.query.filter(
            db.or_(
                db.and_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == partner_id),
                db.and_(ChatMessage.sender_id == partner_id, ChatMessage.receiver_id == user_id)
            )
        ).order_by(ChatMessage.timestamp.asc()).all()
        
        partner = User.query.get(partner_id)
        if not partner:
            return jsonify({"success": False, "message": "Partner not found"}), 404
        
        messages_list = []
        for msg in messages:
            sender = User.query.get(msg.sender_id)
            messages_list.append({
                'id': msg.id,
                'sender_id': msg.sender_id,
                'sender_name': f"{sender.first_name} {sender.last_name}",
                'receiver_id': msg.receiver_id,
                'message': msg.message,
                'timestamp': msg.timestamp.isoformat(),
                'room': msg.room
            })
        
        return jsonify({
            "success": True,
            "messages": messages_list,
            "partner": {
                'id': partner.id,
                'name': f"{partner.first_name} {partner.last_name}",
                'role': partner.role,
                'company': partner.company_name if partner.role == 'employer' else None
            }
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/chat/start/<int:partner_id>', methods=['POST'])
def start_chat(partner_id):
    """Start a new chat conversation or get existing room"""
    try:
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "User not authenticated"}), 401
        
        user_id = session['user_id']
        
        partner = User.query.get(partner_id)
        if not partner:
            return jsonify({"success": False, "message": "Partner not found"}), 404
        
        room = f"chat_{min(user_id, partner_id)}_{max(user_id, partner_id)}"
        
        return jsonify({
            "success": True,
            "room": room,
            "partner": {
                'id': partner.id,
                'name': f"{partner.first_name} {partner.last_name}",
                'role': partner.role,
                'company': partner.company_name if partner.role == 'employer' else None
            }
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Socket.IO Event Handlers

@socketio.on('connect')
def handle_connect():
    """Handle user connection"""
    print(f"User connected: {request.sid}")
    emit('connected', {'message': 'Connected to chat server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection"""
    print(f"User disconnected: {request.sid}")
    for user_id, socket_id in active_users.items():
        if socket_id == request.sid:
            del active_users[user_id]
            break

@socketio.on('join_chat')
def handle_join_chat(data):
    """Handle user joining a chat room"""
    try:
        user_id = data.get('user_id')
        partner_id = data.get('partner_id')
        
        if not user_id or not partner_id:
            emit('error', {'message': 'User ID and Partner ID required'})
            return
        
        room = f"chat_{min(user_id, partner_id)}_{max(user_id, partner_id)}"
        
        # store socket id (sid) so we can target the user's connection correctly
        active_users[user_id] = request.sid
        
        join_room(room)
        
        user = User.query.get(user_id)
        if user:
            emit('joined_room', {
                'room': room,
                'user_name': f"{user.first_name} {user.last_name}",
                'message': f"{user.first_name} joined the chat"
            }, room=room)
        
        print(f"User {user_id} joined room {room}")
        
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('leave_chat')
def handle_leave_chat(data):
    """Handle user leaving a chat room"""
    try:
        user_id = data.get('user_id')
        partner_id = data.get('partner_id')
        
        if not user_id or not partner_id:
            emit('error', {'message': 'User ID and Partner ID required'})
            return
        
        room = f"chat_{min(user_id, partner_id)}_{max(user_id, partner_id)}"
        
        leave_room(room)
        
        user = User.query.get(user_id)
        if user:
            emit('left_room', {
                'room': room,
                'user_name': f"{user.first_name} {user.last_name}",
                'message': f"{user.first_name} left the chat"
            }, room=room)
        
        print(f"User {user_id} left room {room}")
        
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a message"""
    try:
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        message = data.get('message')
        
        if not sender_id or not receiver_id or not message:
            emit('error', {'message': 'Sender ID, Receiver ID, and message are required'})
            return
        
        # Create room name
        room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
        
        # Get sender info
        sender = User.query.get(sender_id)
        if not sender:
            emit('error', {'message': 'Sender not found'})
            return
        
        # Save message to database
        chat_message = ChatMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message,
            room=room,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(chat_message)
        db.session.commit()
        
        # Prepare message data
        message_data = {
            'id': chat_message.id,
            'sender_id': sender_id,
            'sender_name': f"{sender.first_name} {sender.last_name}",
            'receiver_id': receiver_id,
            'message': message,
            'timestamp': chat_message.timestamp.isoformat(),
            'room': room
        }
        
        emit('receive_message', message_data, room=room)
        
        
        print(f"Message sent in room {room}: {message}")
        
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicators"""
    try:
        user_id = data.get('user_id')
        partner_id = data.get('partner_id')
        is_typing = data.get('is_typing', False)
        
        if not user_id or not partner_id:
            emit('error', {'message': 'User ID and Partner ID required'})
            return
        
        # Create room name
        room = f"chat_{min(user_id, partner_id)}_{max(user_id, partner_id)}"
        
        # Get user info
        user = User.query.get(user_id)
        if user:
            # Emit typing status to room (excluding sender)
            emit('user_typing', {
                'user_id': user_id,
                'user_name': f"{user.first_name} {user.last_name}",
                'is_typing': is_typing
            }, room=room, include_self=False)
        
    except Exception as e:
        emit('error', {'message': str(e)})

@app.route('/api/chat/users/search', methods=['GET'])
def search_users():
    """Search for users to start a chat with"""
    try:
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "User not authenticated"}), 401
        
        user_id = session['user_id']
        current_user = User.query.get(user_id)
        
        if not current_user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        search_query = request.args.get('q', '').strip()
        # Filter by role - only allow known roles to avoid typos like "jomsg"
        user_role = request.args.get('role', '').strip()
        allowed_roles = {'job_seeker', 'employer'}
        if user_role and user_role not in allowed_roles:
            return jsonify({"success": False, "message": "Invalid role filter"}), 400
        
        query = User.query.filter(User.id != user_id, User.is_verified == True)
        
        if search_query:
            query = query.filter(
                db.or_(
                    User.first_name.ilike(f'%{search_query}%'),
                    User.last_name.ilike(f'%{search_query}%'),
                    User.company_name.ilike(f'%{search_query}%') if search_query else False
                )
            )
        
        if user_role:
            query = query.filter(User.role == user_role)
        
        if current_user.role == 'job_seeker':
            query = query.filter(User.role == 'employer')
        elif current_user.role == 'employer':
            query = query.filter(User.role == 'job_seeker')
        
        users = query.limit(20).all()
        
        users_list = []
        for user in users:
            users_list.append({
                'id': user.id,
                'name': f"{user.first_name} {user.last_name}",
                'role': user.role,
                'company': user.company_name if user.role == 'employer' else None,
                'email': user.email
            })
        
        return jsonify({"success": True, "users": users_list})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/chat/mark-read/<int:partner_id>', methods=['POST'])
def mark_messages_read(partner_id):
    """Mark all messages from a partner as read"""
    try:
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "User not authenticated"}), 401
        
        user_id = session['user_id']
        
        unread_messages = ChatMessage.query.filter(
            ChatMessage.sender_id == partner_id,
            ChatMessage.receiver_id == user_id,
            ChatMessage.is_read == False
        ).all()
        
        for message in unread_messages:
            message.is_read = True
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Marked {len(unread_messages)} messages as read"
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/chat/unread-count', methods=['GET'])
def get_unread_count():
    """Get total unread message count for current user"""
    try:
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "User not authenticated"}), 401
        
        user_id = session['user_id']
        
        unread_count = ChatMessage.query.filter(
            ChatMessage.receiver_id == user_id,
            ChatMessage.is_read == False
        ).count()
        
        unread_by_sender = db.session.query(
            ChatMessage.sender_id,
            db.func.count(ChatMessage.id).label('count')
        ).filter(
            ChatMessage.receiver_id == user_id,
            ChatMessage.is_read == False
        ).group_by(ChatMessage.sender_id).all()
        
        unread_conversations = {}
        for sender_id, count in unread_by_sender:
            sender = User.query.get(sender_id)
            if sender:
                unread_conversations[sender_id] = {
                    'sender_id': sender_id,
                    'sender_name': f"{sender.first_name} {sender.last_name}",
                    'count': count
                }
        
        return jsonify({
            "success": True,
            "total_unread": unread_count,
            "unread_conversations": list(unread_conversations.values())
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
