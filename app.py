# from shopmate import app,db
# from shopmate.models import User
# from shopmate.utils.reminder_worker import start_scheduler

# if __name__=='__main__':
#     with app.app_context():
#         # db.drop_all()
#         db.create_all()

#         users=User.query.all()
#         import shopmate.routes.set_reminder as rr

#         # for user in users:
#         #     user.is_verified = False
#         # db.session.commit()
#         start_scheduler()
    
#     app.run(debug=True)







# # import eventlet
# # eventlet.monkey_patch()


# # from flask import Flask, request, jsonify
# # from flask_cors import CORS
# # from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
# # from flask_socketio import SocketIO, emit, join_room
# # import config
# # from models import Users, Products, PriceAlerts, UserEvents
# # from services.product_search import search_products
# # from services.recommender import recommend_for_user
# # from nlp.nlu import parse_intent
# # from services.alerts import schedule_price_alert
# # from tasks.celery_tasks import celery

# # app = Flask(__name__)
# # app.config["JWT_SECRET_KEY"] = config.JWT_SECRET
# # CORS(app)
# # jwt = JWTManager(app)
# # socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# # @app.route("/api/register", methods=["POST"])
# # def register():
# #     data = request.json
# #     if Users.find_one({"email": data["email"]}):
# #         return jsonify({"msg":"user exists"}), 400
# #     Users.insert_one({"email": data["email"], "name": data.get("name"), "prefs": {}, "history": []})
# #     return jsonify({"msg":"registered"}), 201

# # @app.route("/api/login", methods=["POST"])
# # def login():
# #     data = request.json
# #     user = Users.find_one({"email": data["email"]})
# #     if not user:
# #         return jsonify({"msg":"no user"}), 404
# #     token = create_access_token(identity=str(user["_id"]))
# #     return jsonify({"access_token": token})

# # @app.route("/api/search")
# # # @jwt_required()
# # def api_search():
# #     print("Called search")
# #     q = request.args.get("q")
# #     # user_id = get_jwt_identity()
# #     # parse intent (e.g., filter, price range, category)
# #     intent = parse_intent(q)
# #     results = search_products(q, intent)
# #     # log event
# #     # UserEvents.insert_one({"user_id": user_id, "type": "search", "query": q})
# #     return jsonify({"results": results})

# # @app.route("/api/recommend")
# # @jwt_required()
# # def api_recommend():
# #     user_id = get_jwt_identity()
# #     recs = recommend_for_user(user_id)
# #     return jsonify({"recommendations": recs})

# # @app.route("/api/price-alert", methods=["POST"])
# # @jwt_required()
# # def set_price_alert():
# #     user_id = get_jwt_identity()
# #     body = request.json
# #     alert_id = PriceAlerts.insert_one({"user_id": user_id, **body}).inserted_id
# #     schedule_price_alert(str(alert_id))
# #     return jsonify({"msg":"alert scheduled", "id": str(alert_id)})


# # @app.route("/chat", methods=["POST"])
# # def chat():
# #     data = request.get_json()
# #     return jsonify({"reply": "Hello!"})


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)
from medjobhub import app, db, socketio
from medjobhub.models import User
if __name__ == '__main__':
    with app.app_context():
        # db.drop_all()
        db.create_all()
        
        users = User.query.all()
        for user in users:
            user.is_verified = False
        db.session.commit()

    socketio.run(app, debug=True, port=5001, allow_unsafe_werkzeug=True)
