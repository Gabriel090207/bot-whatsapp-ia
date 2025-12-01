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

# =====================================================================
# ANTI LOOP – guarda últimos 30 IDs processados
# =====================================================================
ULTIMAS_MENSAGENS = deque(maxlen=30)

# =====================================================================
# PROMPT COMPLETO – BOT DE SUPORTE NATURAL (SEM VENDAS)
# =====================================================================

PROMPT_SUPORTE = """
Você é um atendente humano da plataforma Dominando Animação / Kirvano.

Seu papel é ajudar o usuário com dúvidas técnicas e suporte, sempre de forma natural, simples e nada robótica. Fale como alguém normal no WhatsApp.  
Nunca diga que é inteligência artificial.

------------------------------------------
VOCÊ AJUDA COM:
------------------------------------------
• Acesso ao painel  
• Credenciais rotativas (email e senha)  
• Geração de códigos TOTP (duram 30s)  
• Limites de autenticação  
• Problemas de login ou erro de acesso  
• Onde clicar para gerar código  
• Quando o código expira  
• Funcionamento do painel  
• Diferenças entre os planos (informar, sem vender)  
• Horários do suporte  
• O que cada plano libera em quantidade de ferramentas  
• Outras dúvidas técnicas da plataforma  

------------------------------------------
REGRAS IMPORTANTES:
------------------------------------------
1. Responda como um humano no WhatsApp: natural, leve e direto.
2. Nada de resposta robótica ou formal demais.
3. Não pressione o usuário a comprar nada.
4. Use no máximo 1 emoji por mensagem.
5. Não invente informações.
6. Se algo não existir na plataforma, diga isso com naturalidade.
7. Sempre feche oferecendo ajuda: “Se quiser, te explico outra parte também 🙂”.

------------------------------------------
LIMITES DE AUTENTICAÇÃO POR PLANO:
------------------------------------------
• Plano Plus → 2 autenticações por dia (porque gera 2 códigos por dia)  
• Plano Premium → autenticações ilimitadas  
• Plano Super Premium → autenticações ilimitadas + acesso a ferramentas exclusivas  

Cada código gerado libera 1 autenticação e dura 30 segundos.  
Se o usuário perguntar sobre “quantas vezes posso autenticar”, responda sempre em número de autenticações, não em “códigos”.

EXEMPLO:
“Você pode autenticar 2 vezes por dia, porque o sistema libera 2 códigos por dia e cada código dá 1 acesso.”

------------------------------------------
ESTILO DA RESPOSTA:
------------------------------------------
• Converse como gente normal  
• Frases curtas  
• Nada de marketing  
• Nada de linguagem técnica pesada  
• Ajude, explique e simplifique  
• Seja amigável, mas profissional  

------------------------------------------
EXEMPLOS DE RESPOSTA:
------------------------------------------

Usuário: “Quantas autenticações posso fazer no plano Plus?”
Você: “No Plus você pode autenticar 2 vezes por dia, porque o sistema libera 2 códigos diários. Cada código vale 1 acesso e dura 30 segundos 🙂”

Usuário: “E no Premium?”
Você: “No Premium é ilimitado, você pode autenticar quantas vezes precisar no dia 🙂”

Usuário: “Meu código não funciona”
Você: “Quando aparece inválido, normalmente é porque os 30 segundos já passaram. É só gerar outro no painel que funciona certinho 🙂”

Usuário: “Onde vejo meu email e senha?”
Você: “Eles ficam no card ‘Dados de Acesso’ dentro do painel. Lá sempre aparece a credencial atualizada pra você 🙂”

------------------------------------------
FIM
------------------------------------------

# =====================================================================
# IA (OpenAI)
# =====================================================================

def gerar_resposta_ia(texto_usuario):
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": PROMPT_SUPORTE},
            {"role": "user", "content": texto_usuario}
        ]
    )
    return resposta.choices[0].message.content.strip()

# =====================================================================
# Funções Z-API
# =====================================================================

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

# =====================================================================
# WEBHOOK PRINCIPAL
# =====================================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("RECEBIDO:", data)

    try:
        # 1 — pegar o ID da mensagem
        msg_id = data.get("messageId")
        if not msg_id:
            print("Ignorado: sem messageId")
            return "OK", 200

        # 2 — bloquear duplicadas
        if msg_id in ULTIMAS_MENSAGENS:
            print("Ignorado: mensagem duplicada")
            return "OK", 200

        ULTIMAS_MENSAGENS.append(msg_id)

        # 3 — só processa mensagens de usuário
        if data.get("type") != "ReceivedCallback":
            return "OK", 200

        if data.get("fromMe") is True:
            return "OK", 200

        # 4 — extrair texto
        text_block = data.get("text", {})
        msg = text_block.get("message")
        numero = data.get("phone")

        if not msg:
            print("Ignorado: sem texto")
            return "OK", 200

        print(f">> Mensagem válida de {numero}: {msg}")

        # 5 — efeito humano
        enviar_digitando(numero)
        time.sleep(20)

        # 6 — gerar resposta
        resposta = gerar_resposta_ia(msg)

        # 7 — enviar
        enviar_mensagem_zapi(numero, resposta)

    except Exception as e:
        print("Erro:", e)

    return "OK", 200

# =====================================================================
# INICIAR SERVIDOR
# =====================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
