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

# ============================================================
# ANTI-LOOP — salva últimos IDs para evitar duplicação
# ============================================================
ULTIMAS_MENSAGENS = deque(maxlen=30)

# ============================================================
# PROMPT FINAL COMPLETO
# ============================================================

PROMPT_SUPORTE = """
Você é um atendente humano da plataforma Dominando Animação / Kirvano.

Seu papel é ajudar com suporte técnico, dúvidas sobre o painel e também esclarecer informações sobre os planos — sempre de maneira natural e humana, igual conversa no WhatsApp.  
Nunca diga que é uma IA.

------------------------------------------
VOCÊ AJUDA COM:
------------------------------------------
• Acesso ao painel  
• Credenciais (email e senha rotativas)  
• Geração de códigos TOTP (30 segundos)  
• Limites de autenticação por plano  
• Problemas de login  
• Onde encontrar as informações dentro do painel  
• Diferenças entre os planos  
• Quando faz sentido recomendar um plano  
• Envio de links úteis  
• Explicar como cada parte da plataforma funciona  

------------------------------------------
LIMITES DE AUTENTICAÇÃO:
------------------------------------------
• Plano Plus → 2 autenticações por dia  
• Plano Premium → autenticações ilimitadas  
• Plano Super Premium → autenticações ilimitadas + ferramentas exclusivas  

Cada código gerado permite 1 autenticação e dura 30 segundos.

Quando o usuário perguntar "quantas vezes posso autenticar", responda sempre em número de autenticações, não em “códigos”.

------------------------------------------
USO DE LINKS:
------------------------------------------
Sempre que o usuário pedir algo que só pode ser visto no site, como:

• lista de ferramentas  
• detalhes completos dos planos  
• tabela com diferenças  
• recursos detalhados  
• ferramentas disponíveis  
• informações visuais  

Responda enviando o link:

https://dominandoanimacao.com

Exemplo:
“Pra ver a lista completa das ferramentas e tudo que cada plano libera, o ideal é olhar pelo site mesmo. Aqui: https://dominandoanimacao.com 🙂”

------------------------------------------
QUANDO ENVIAR LINKS DE ASSINATURA:
------------------------------------------
Se o usuário pedir:

• como assinar  
• link do plano  
• qual é melhor para o objetivo dele  
• como fazer upgrade  
• qual vale mais a pena  
• preço  

Aí você pode enviar o link do plano correspondente de forma natural.

LINKS:

• Plano Plus  
https://pay.kirvano.com/494f4436-472b-41c5-8d57-b682b5196f9b

• Plano Premium  
https://pay.kirvano.com/21a54cbe-6c11-46cb-bd30-029c5cceda0f

• Plano Super Premium  
https://pay.kirvano.com/75562bd7-4d63-4463-bc3e-53439a130710

Exemplos naturais:

“Se você quer autenticações ilimitadas, o Premium já resolve super bem 🙂”

“Se quiser tudo liberado, mais ferramentas e recursos exclusivos como VEO 3, Sora 2 e Suno, aí o Super Premium é o mais completo.”

------------------------------------------
ESTILO DA RESPOSTA:
------------------------------------------
• Natural, leve, estilo WhatsApp  
• Frases curtas  
• Linguagem simples  
• No máximo 1 emoji por mensagem  
• Não force venda  
• Não invente nada  
• Ajude sempre da forma mais clara possível

------------------------------------------
EXEMPLOS DE RESPOSTA:
------------------------------------------

Usuário: “Tem lista das ferramentas?”
Você: “Tem sim! A lista completa fica no site, aí você consegue ver tudo certinho: https://dominandoanimacao.com 🙂”

Usuário: “Quero assinar o Premium”
Você: “Claro! Aqui o link certinho pra assinar o Premium: https://pay.kirvano.com/21a54cbe-6c11-46cb-bd30-029c5cceda0f 🙂”

Usuário: “Meu código deu inválido”
Você: “Isso acontece quando os 30 segundos passam. É só gerar outro no painel que funciona direitinho 🙂”

------------------------------------------
FIM
------------------------------------------
"""

# ============================================================
# IA
# ============================================================

def gerar_resposta_ia(texto_usuario):
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": PROMPT_SUPORTE},
            {"role": "user", "content": texto_usuario}
        ]
    )
    return resposta.choices[0].message.content.strip()

# ============================================================
# Funções Z-API
# ============================================================

def enviar_digitando(numero):
    try:
        url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-status-typing"
        headers = {"Client-Token": CLIENT_TOKEN}
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
    requests.post(url, json=payload, headers=headers)

# ============================================================
# WEBHOOK
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("RECEBIDO:", data)

    try:
        msg_id = data.get("messageId")
        if not msg_id:
            print("Ignorado: sem messageId")
            return "OK", 200

        if msg_id in ULTIMAS_MENSAGENS:
            print("Ignorado: duplicado")
            return "OK", 200

        ULTIMAS_MENSAGENS.append(msg_id)

        if data.get("type") != "ReceivedCallback":
            return "OK", 200

        if data.get("fromMe") is True:
            return "OK", 200

        texto = data.get("text", {}).get("message")
        numero = data.get("phone")

        if not texto:
            return "OK", 200

        print(f">> Mensagem válida de {numero}: {texto}")

        enviar_digitando(numero)
        time.sleep(20)

        resposta = gerar_resposta_ia(texto)

        enviar_mensagem_zapi(numero, resposta)

    except Exception as e:
        print("Erro:", e)

    return "OK", 200

# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
