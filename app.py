import os
from flask import Flask, request
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Carrega variáveis de ambiente
INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
INSTANCE_TOKEN = os.getenv("ZAPI_TOKEN")
CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("DEBUG - CLIENT TOKEN:", CLIENT_TOKEN)    # <– PARA VER NO LOG DO RENDER

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

def gerar_resposta_ia(texto):
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um atendente amigável."},
            {"role": "user", "content": texto}
        ]
    )
    return resposta.choices[0].message.content.strip()


def enviar_mensagem_zapi(numero, texto):
    url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-text"

    payload = {
        "phone": numero,
        "message": texto
    }

    headers = {
        "Client-Token": CLIENT_TOKEN,
        "Content-Type": "application/json"
    }

    resposta = requests.post(url, json=payload, headers=headers)
    print("Resposta da Z-API:", resposta.status_code, resposta.text)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("RECEBIDO DA Z-API:", data)

    try:
        msg = data["text"]["message"]
        numero = data["phone"]

        print(f">> Mensagem recebida de {numero}: {msg}")

        resposta = gerar_resposta_ia(msg)

        enviar_mensagem_zapi(numero, resposta)

    except Exception as erro:
        print("Erro ao processar webhook:", erro)

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
