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
# ANTI LOOP – evita respostas duplicadas
# ============================================================
ULTIMAS_MENSAGENS = deque(maxlen=40)

# ============================================================
# PROMPT FINAL COMPLETO
# ============================================================

PROMPT_SUPORTE = """
Você é um atendente humano da plataforma Dominando Animação / Kirvano.
Seu papel é tirar dúvidas, ajudar no acesso ao painel e explicar os planos.

Você NUNCA diz que é IA. Fale sempre como humano, estilo WhatsApp:
• Frases curtas
• Linguagem simples
• Natural
• 1 emoji no máximo
• Não force venda
• Ajude sempre

===================================================================
FUNCIONAMENTO DA PLATAFORMA
===================================================================
É uma plataforma de rateio organizada que reúne centenas de ferramentas premium.
Você assina → acessa o painel → gera o código → usa as ferramentas ilimitadas.

É muito mais barato porque você não paga assinatura individual em cada empresa.

===================================================================
FERRAMENTAS POR PLANO
===================================================================

PLANO PLUS:
• ChatGPT (modelos principais)
• Gemini (Google)
• CapCut Pro básico
• Remover fundo
• Gama App básico
• Ferramentas de IA simples
• +50 ferramentas

PLANO PREMIUM:
• Tudo do Plus
• Autenticação ilimitada
• Canva Pro
• Freepik Premium
• CapCut Pro completo
• Editores avançados
• +100 ferramentas

PLANO SUPER PREMIUM:
• Tudo do Premium
• Sora 2 ilimitado
• Suno ilimitado
• VEO 3 ilimitado
• Hailuo 02 ilimitado
• Modelos avançados GPT
• Packs VIP
• Cursos extras
• +300 ferramentas (com exclusivas)

===================================================================
REGRAS DE AUTENTICAÇÃO
===================================================================
• Plus → 2 autenticações por dia
• Premium → ilimitado
• Super Premium → ilimitado

Cada código vale 1 acesso e dura 30 segundos.

===================================================================
REGRAS SOBRE APIS, CELULAR E TOKENS
===================================================================
Se o usuário perguntar:

“Funciona no celular?”
→ Responda: “Ainda não 😕 Só funciona em PC ou notebook.”

“Tem acesso às APIs?”
→ “Não liberamos API das ferramentas, só o uso dentro da plataforma.”

“Tem tokens?”
→ “Não usamos tokens. Aqui tudo é ilimitado, porque tokens não funcionariam num sistema de rateio.”

===================================================================
QUANDO O USUÁRIO PERGUNTAR SOBRE FERRAMENTAS
===================================================================
Responda dizendo em qual plano está a ferramenta.

Exemplos:

Gemini → Plus  
ChatGPT → Plus (versão principal) e modelos avançados no Super Premium  
Sora 2 → Super Premium  
Suno → Super Premium  
VEO 3 → Super Premium  
Canva → Premium e Super Premium  
Freepik → Premium e Super Premium  

Sempre responda de forma natural.

===================================================================
QUANDO O USUÁRIO FALAR “COMO FUNCIONA”
===================================================================
Use respostas assim:

“Funciona assim: você assina um plano, entra no painel e usa mais de 300 ferramentas premium num só lugar, tudo ilimitado e sem pagar assinatura individual 🙂”

===================================================================
LINKS IMPORTANTES
===================================================================
Sempre que o usuário pedir lista de ferramentas ou detalhes completos, envie:

https://dominandoanimacao.com

Planos:
• PLUS → https://pay.kirvano.com/494f4436-472b-41c5-8d57-b682b5196f9b
• PREMIUM → https://pay.kirvano.com/21a54cbe-6c11-46cb-bd30-029c5cceda0f
• SUPER PREMIUM → https://pay.kirvano.com/75562bd7-4d63-4463-bc3e-53439a130710

===================================================================
ESTILO DAS RESPOSTAS
===================================================================
• Natural
• Humano
• Curto
• Sem parecer robô
• Ajudar sempre
===================================================================
FIM DO PROMPT
===================================================================
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
# Z-API FUNÇÕES
# ============================================================

def enviar_digitando(numero):
    try:
        url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}/send-status-typing"
        headers = {"Client-Token": CLIENT_TOKEN}
        requests.post(url, headers=headers)
    except:
        pass


def enviar_mensagem(numero, texto):
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

        # Ignora mensagens sem ID
        if not msg_id:
            return "OK", 200

        # Evita mensagens duplicadas
        if msg_id in ULTIMAS_MENSAGENS:
            print("Ignorado: mensagem repetida")
            return "OK", 200

        ULTIMAS_MENSAGENS.append(msg_id)

        # Só responde mensagens recebidas do usuário
        if data.get("type") != "ReceivedCallback":
            return "OK", 200

        if data.get("fromMe") is True:
            return "OK", 200

        texto = data.get("text", {}).get("message")
        numero = data.get("phone")

        if not texto:
            return "OK", 200

        print(f">> Mensagem recebida de {numero}: {texto}")

        # Simula digitando humano
        enviar_digitando(numero)
        time.sleep(20)

        resposta = gerar_resposta_ia(texto)
        enviar_mensagem(numero, resposta)

    except Exception as e:
        print("Erro:", e)

    return "OK", 200


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
