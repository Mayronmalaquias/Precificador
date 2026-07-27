import uuid
import traceback
from flask import request
from flask_restx import Namespace, Resource

from app.services.chat_service import chat

chat_ns = Namespace("chat", description="Assistente virtual IA")


@chat_ns.route("/chat")
class ChatResource(Resource):
    def post(self):
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return {"erro": "Campo 'message' é obrigatório"}, 400

        session_id = data.get("session_id") or str(uuid.uuid4())

        try:
            resposta = chat(session_id, user_message)
            return {"resposta": resposta, "session_id": session_id}
        except Exception as e:
            traceback.print_exc()
            return {"erro": str(e)}, 500
