import os
from flask import Flask, request
import requests
from dotenv import load_dotenv
from openai import OpenAI

# Carrega as variáveis do arquivo .env
load_dotenv()

# Lê as variáveis de ambiente
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicializa cliente da OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

def gerar_resposta_ia(texto_usuario: str) -> str:
    """
    Usa o modelo da OpenAI pra gerar uma resposta bem humanizada.
    """
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um atendente de WhatsApp brasileiro, educado, "
                    "informal na medida certa, responde de forma clara e simples, "
                    "e tenta ajudar sempre. Evite respostas muito longas."
                )
            },
            {
                "role": "user",
                "content": texto_usuario
            }
        ]
    )

    return resposta.choices[0].message.content.strip()

def enviar_mensagem_whatsapp(numero: str, texto: str):
    """
    Envia uma mensagem para o WhatsApp usando a WhatsApp Cloud API.
    """
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {
            "body": texto
        }
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }

    resposta = requests.post(url, json=payload, headers=headers)
    print("Resposta da API do WhatsApp:", resposta.status_code, resposta.text)

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """
    Endpoint de verificação usado pela Meta para validar o webhook.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        print("Webhook verificado com sucesso!")
        return challenge, 200
    else:
        print("Falha na verificação do webhook.")
        return "Erro de verificação", 403

@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    """
    Recebe mensagens reais enviadas pelo WhatsApp.
    """
    data = request.get_json()
    print("Recebido do WhatsApp:", data)

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" in value:
            message = value["messages"][0]
            numero = message["from"]
            texto_usuario = None

            if message.get("type") == "text":
                texto_usuario = message["text"]["body"]

            if texto_usuario:
                print(f"Mensagem de {numero}: {texto_usuario}")

                resposta_ia = gerar_resposta_ia(texto_usuario)

                enviar_mensagem_whatsapp(numero, resposta_ia)

    except Exception as e:
        print("Erro ao processar mensagem:", e)

    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

