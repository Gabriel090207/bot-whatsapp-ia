import os
import time
import requests
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI
from collections import deque

load_dotenv()

INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
INSTANCE_TOKEN = os.getenv("ZAPI_TOKEN")
CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# 🔒 ARMAZENAR OS ÚLTIMOS IDs PARA EVITAR MENSAGENS DUPLICADAS
ULTIMAS_MENSAGENS = deque(maxlen=30)

# 🔥 PROMPT ATUALIZADO
PROMPT_SUPORTE = """
Você é um atendente humano...
(igual ao anterior, exatamente como te passei)
"""

def gerar_resposta_ia(texto_usuario):
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": PROMPT_SUPORTE},
            {"role": "user", "content": texto_usuario}
        ]
    )
    return resposta.choices[0].message.content.strip()

def enviar_digitando(numero):
    url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-status-typing"
    headers = {"Client-Token": CLIENT_TOKEN}
    try:
        requests.post(url, headers=headers)
    except:
        pass

def enviar_mensagem_zapi(numero, texto):
    url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-text"
    headers = {
        "Client-Token": CLIENT_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {"phone": numero, "message": texto}
    requests.post(url, headers=headers, json=payload)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("RECEBIDO:", data)

    try:
        # ⚠️ 1. VERIFICAR SE TEM ID ÚNICO
        msg_id = data.get("messageId") or data.get("id") or None

        if not msg_id:
            print("Sem ID → Ignorado.")
            return "OK", 200

        # ⚠️ 2. SE JÁ PROCESSOU ESSE ID → IGNORA
        if msg_id in ULTIMAS_MENSAGENS:
            print("Mensagem duplicada → Ignorada.")
            return "OK", 200

        # salvar ID para evitar repetição
        ULTIMAS_MENSAGENS.append(msg_id)

        # ⚠️ 3. VALIDAR QUE É CHAT DO USUÁRIO
        if "text" not in data:
            return "IGNORADO", 200

        text_block = data.get("text", {})
        msg = text_block.get("message")
        numero = data.get("phone")

        if not msg:
            return "IGNORADO", 200

        if text_block.get("fromMe"):
            return "IGNORADO", 200

        if text_block.get("type") != "chat":
            return "IGNORADO", 200

        print(f">> Mensagem válida de {numero}: {msg}")

        # Processar normalmente
        enviar_digitando(numero)
        time.sleep(20)

        resposta = gerar_resposta_ia(msg)
        enviar_mensagem_zapi(numero, resposta)

    except Exception as e:
        print("Erro:", e)

    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
