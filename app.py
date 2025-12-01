import os
from flask import Flask, request
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

def gerar_resposta_ia(texto_usuario: str) -> str:
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um atendente de WhatsApp brasileiro, educado e prestativo. "
                    "Responda de forma simples, natural e humana."
                )
            },
            {
                "role": "user",
                "content": texto_usuario
            }
        ]
    )
    return resposta.choices[0].message.content.strip()

def enviar_mensagem(numero: str, texto: str):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    
    payload = {
        "phone": numero,
        "message": texto
    }

    headers = {"Content-Type": "application/json"}

    r = requests.post(url, json=payload, headers=headers)
    print("Resposta da Z-API:", r.status_code, r.text)

@app.route("/webhook", methods=["POST"])
def receber_webhook():
    try:
        data = request.get_json()
        print("RECEBIDO DA Z-API:", data)

        if "text" in data and "message" in data["text"]:
            texto = data["text"]["message"]
            numero = data["phone"]

            print(f">> Mensagem recebida de {numero}: {texto}")

            resposta = gerar_resposta_ia(texto)
            enviar_mensagem(numero, resposta)

        else:
            print("⚠️ Nenhuma mensagem de texto encontrada.")

    except Exception as e:
        print("Erro ao processar webhook:", e)

    return "OK", 200

@app.route("/")
def home():
    return "BOT ONLINE"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
