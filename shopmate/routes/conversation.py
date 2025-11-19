from flask import jsonify, request
from shopmate import app, db, allowed_url,cross_origin,datetime
from shopmate.models import Conversation, Message


# ✅ Create conversation
@app.route('/conversation', methods=['POST', 'OPTIONS'])
@cross_origin(origins=["http://localhost:5173", "http://127.0.0.1:5173"], supports_credentials=True)
def create_conversation():
    data = request.get_json() or {}
    title = data.get('title', 'New Conversation')
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    new_conversation = Conversation(user_id=user_id, title=title)
    db.session.add(new_conversation)
    db.session.commit()

    intro_msg = Message(
        conversation_id=new_conversation.id,
        role="assistant",
        content=(
            "👋 **Welcome to ShopMate!**\n\n"
            "I’m your smart shopping assistant — I can help you compare Amazon/Flipkart products, "
            "find the best deals, check reviews, analyze features, and more!\n\n"
            "Tell me what you want to explore today. 🛍️✨"
        )
    )
    db.session.add(intro_msg)
    db.session.commit()

    return jsonify({
        'success': True,
        'conversation': {
            'id': new_conversation.id,
            'title': new_conversation.title,
            'user_id': new_conversation.user_id,
            'created_at': new_conversation.created_at.isoformat(),
            'updated_at': new_conversation.updated_at.isoformat()
        }
    }), 201


# ✅ Get all conversations
# @app.route('/conversations', methods=['GET', 'OPTIONS'])
# def get_conversations():
#     conversations = Conversation.query.order_by(Conversation.updated_at.desc()).all()

#     return jsonify({
#         'conversations': [{
#             'id': conv.id,
#             'title': conv.title,
#             'created_at': conv.created_at.isoformat(),
#             'updated_at': conv.updated_at.isoformat()
#         } for conv in conversations]
#     }), 200

@app.route('/conversations/<int:user_id>', methods=['GET', 'OPTIONS'])
def get_conversations_by_user(user_id):
    # Fetch only conversations that belong to the user
    conversations = (
        Conversation.query
        .filter_by(user_id=user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    if not conversations:
        return jsonify({'message': 'No conversations found for this user', 'conversations': []}), 200

    return jsonify({
        'conversations': [{
            'id': conv.id,
            'title': conv.title,
            'user_id': conv.user_id,
            'created_at': conv.created_at.isoformat(),
            'updated_at': conv.updated_at.isoformat()
        } for conv in conversations]
    }), 200

# ✅ Get specific conversation
@app.route('/conversation/<int:conversation_id>', methods=['GET', 'OPTIONS'])
def get_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)

    messages = (
        Message.query
        .filter_by(conversation_id=conversation_id)
        .order_by(Message.timestamp)
        .all()
    )

    return jsonify({
        'conversation': {
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat()
        },
        'messages': [{
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),

            'products': msg.products or [],
            'price_history': getattr(msg, "price_history", None),
            'price_prediction': getattr(msg, "price_prediction", None),
            'reviews': getattr(msg, "reviews", None),

        } for msg in messages]
    }), 200


# ✅ Delete conversation
@app.route('/conversation/<int:conversation_id>', methods=['DELETE', 'OPTIONS'])
def delete_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Conversation deleted'}), 200


@app.route('/conversation/<int:conversation_id>', methods=['PUT'])
@cross_origin(origins=["http://localhost:5173", "http://127.0.0.1:5173"], supports_credentials=True)
def update_conversation(conversation_id):
    data = request.get_json() or {}
    new_title = data.get('title')

    conversation = Conversation.query.get_or_404(conversation_id)

    if new_title:
        conversation.title = new_title

    conversation.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'conversation': {
            'id': conversation.id,
            'title': conversation.title,
            'updated_at': conversation.updated_at.isoformat(),
        }
    }), 200
