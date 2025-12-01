import os
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
from openai import OpenAI

# ⚠️ Carregar .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ⚠️ Configuração Z-API
INSTANCE_ID = "3EB0D956FE2A30E093AF4EAB8513EE1E"
INSTANCE_TOKEN = "2E7ADF233725BCA0BA329488"

ZAPI_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-text"

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)


# 🔥 GERAR RESPOSTA COM OPENAI
def gerar_resposta_ia(texto_usuario):
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", 
             "content": "Você é um atendente humano, amigável, educado e direto nas respostas."},
            {"role": "user", "content": texto_usuario}
        ]
    )
    return resposta.choices[0].message.content


# 🔥 ENVIAR MENSAGEM PARA O WHATSAPP (Z-API)
def enviar_mensagem(numero, texto):
    payload = {
        "phone": numero,
        "message": texto
    }
    r = requests.post(ZAPI_URL, json=payload)
    print("Resposta Z-API:", r.text)


# 🔥 ROTA DE TESTE
@app.route("/")
def home():
    return "Bot WhatsApp com Z-API está rodando!", 200


# 🔥 ROTA DO WEBHOOK (recebe mensagem e responde)
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("RECEBIDO DA Z-API:", data)

    try:
        numero = data["message"]["phone"]
        texto = data["message"]["text"]["message"]

        print(f"Mensagem recebida de {numero}: {texto}")

        resposta = gerar_resposta_ia(texto)

        enviar_mensagem(numero, resposta)

    except Exception as e:
        print("Erro ao processar webhook:", e)

    return jsonify({"status": "OK"}), 200


# 🔥 RENDER EXIGE ESSA PORTA
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
