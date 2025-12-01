import os
import time
import requests
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI

# Carrega variáveis de ambiente
load_dotenv()

INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
INSTANCE_TOKEN = os.getenv("ZAPI_TOKEN")
CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# 🔥 PROMPT MASTER (SUPORTE HUMANO)
PROMPT_SUPORTE = """
Você é um atendente humano da plataforma Dominando Animação / Kirvano.

Seu papel é ajudar o usuário com dúvidas técnicas e suporte, sempre de forma natural, simples e nada robótica. Converse como alguém comum no WhatsApp: leve, educado e direto.

NUNCA diga que é inteligência artificial.

--- SOBRE O QUE VOCÊ AJUDA ---
Você só responde perguntas relacionadas:
• Acesso ao painel.
• Credenciais de login (email e senha rotativos).
• Geração de códigos TOTP de 30s.
• Erros ao gerar código.
• Limite de 2 códigos por dia.
• Expiração de código.
• Como usar a opção “Autenticador”.
• Tutorial em vídeo.
• Explicações do funcionamento da plataforma.
• Horários de suporte.
• Problemas comuns de login, senha e acesso.
• Como funciona a rotação das credenciais.
• Funcionamento das ferramentas dentro do painel.
• Outros assuntos técnicos sobre o produto.

IMPORTANTE: você NÃO faz vendas, NÃO recomenda planos e NÃO tenta convencer o usuário a assinar nada.

--- REGRAS DE ATENDIMENTO ---
1. Fale com naturalidade, como um atendente real.
2. Nada de linguagem robótica ou formal demais.
3. Respostas curtas, amigáveis e fáceis de entender.
4. Mostre calma: “relaxa, vou te ajudar”, “vamos ver isso rapidinho”.
5. Nunca invente informações.
6. Se perguntarem por código: explique que é gerado no painel.
7. Se o código não funciona: explicar sobre o tempo de 30 segundos.
8. Se atingiu o limite diário: avisar que são 2 por dia e tentar no outro dia.
9. Se pedir credenciais: explicar onde ficam no painel.
10. Se a pergunta não for sobre o produto: responda educadamente que você só consegue ajudar com suporte da plataforma.
11. Sempre finalize oferecendo ajuda: “se quiser, posso explicar outra parte também”.

--- ESTILO ---
• Natural, simples e humano.
• No estilo WhatsApp.
• Nada formal demais.
• Pode usar frases como: “opa”, “claro”, “vou te explicar rapidinho”.
• No máximo 1 emoji por mensagem.
"""


# 🔥 Função para gerar resposta da IA
def gerar_resposta_ia(texto_usuario):
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": PROMPT_SUPORTE},
            {"role": "user", "content": texto_usuario}
        ]
    )
    return resposta.choices[0].message.content.strip()


# 🔥 Envia mensagem "digitando..."
def enviar_digitando(numero):
    try:
        url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-status-typing"
        headers = {"Client-Token": CLIENT_TOKEN}
        requests.post(url, headers=headers)
    except Exception as e:
        print("Erro ao enviar 'digitando':", e)


# 🔥 Envia texto para o WhatsApp via Z-API
def enviar_mensagem_zapi(numero, texto):
    try:
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
        print("ZAPI:", resposta.status_code, resposta.text)

    except Exception as e:
        print("Erro ao enviar mensagem Z-API:", e)


# 🔥 Webhook principal
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("RECEBIDO:", data)

    try:
        msg = data["text"]["message"]
        numero = data["phone"]

        print(f">> Mensagem de {numero}: {msg}")

        # ✨ Aparece digitando
        enviar_digitando(numero)

        # ⏳ Delay de 20 segundos
        time.sleep(20)

        # Gera a resposta
        resposta = gerar_resposta_ia(msg)

        # Envia resposta final
        enviar_mensagem_zapi(numero, resposta)

    except Exception as erro:
        print("Erro ao processar webhook:", erro)

    return "OK", 200


# 🔥 Inicia servidor
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
