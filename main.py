import feedparser
import requests
import time
import calendar
import os
from google import genai
from google.genai import types
from datetime import datetime, timedelta, timezone

# --- CREDENCIAIS ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

client = genai.Client(api_key=GEMINI_API_KEY)

# --- FONTES EXPANDIDAS ---
FEEDS = [
    'https://www.poder360.com.br/feed/',
    'https://g1.globo.com/rss/g1/politica/',
    'https://www.metropoles.com/feed',
    'https://noticias.uol.com.br/politica/rss.xml',
    'https://www.cartacapital.com.br/politica/feed/',
    'https://oantagonista.com.br/feed/',
    'https://bsky.app/profile/andreiasadi.bsky.social/rss',
    'https://bsky.app/profile/igorgadelha.bsky.social/rss',
    'https://bsky.app/profile/octavio-guedes.bsky.social/rss',
    'https://bsky.app/profile/camilabomfim.bsky.social/rss',
    'https://hugogloss.uol.com.br/feed/',
    'https://trends.google.com/trends/trendingsearches/daily/rss?geo=BR'
]

# --- CÉREBRO DA IA (System Instruction) ---
CONTEXTO = """Você é um curador de informações estratégicas. 

Foco do usuário: 
- Governo Federal, EBC, regras de publicidade legal, Diário Oficial, concursos e eleições.
- Infraestrutura e mobilidade no DF e Consórcio Intermunicipal do Entorno.
- Assuntos pop em alta e tendências virais de impacto.

SUA TAREFA:
1. Ignore intrigas e fofocas irrelevantes.
2. Agrupe as matérias do mesmo tema.
3. Resuma de forma limpa.

FORMATO DE SAÍDA (HTML):
🚨 <b>Radar Atualizado</b>

🔹 <b>[Assunto]</b>
[Resumo]
🔗 <a href="link">Fonte 1</a>

REGRA: Se nada for relevante, responda EXATAMENTE: VAZIO
"""

def enviar_telegram(mensagem):
    # Fatiamento de segurança para não ultrapassar o limite de 4096 caracteres do Telegram
    partes = [mensagem[i:i+4000] for i in range(0, len(mensagem), 4000)]
    for parte in partes:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': CHAT_ID, 'text': parte, 'parse_mode': 'HTML'}
        requests.post(url, data=payload)

def analisar_bloco_com_ia(lista_noticias):
    prompt = "=== NOTÍCIAS RECENTES ===\n" + "\n".join(lista_noticias)
    
    try:
        # Usa o system_instruction para forçar a IA a não sair do personagem
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=CONTEXTO,
                temperature=0.3
            )
        )
        texto_final = response.text.strip()
        
        if texto_final.upper() != "VAZIO" and texto_final:
            texto_final = texto_final.replace("```html", "").replace("```", "").strip()
            enviar_telegram(texto_final)
            print("Boletim enviado com sucesso!")
        else:
            print("Nenhuma relevância encontrada pela IA.")
            
    except Exception as e:
        print(f"Erro na IA: {e}")

def buscar_furos():
    agora = datetime.now(timezone.utc)
    margem_tempo = agora - timedelta(minutes=15)
    noticias_coletadas = []
    
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for artigo in feed.entries:
                # Bypass: Evita quebra caso o RSS (como Hugo Gloss/Trends) omita a data estruturada
                if not hasattr(artigo, 'published_parsed') or not artigo.published_parsed:
                    continue
                
                # Transformação: calendar.timegm previne falhas de fuso horário local que o time.mktime gera em servidores
                data_artigo = datetime.fromtimestamp(calendar.timegm(artigo.published_parsed), timezone.utc)
                
                if data_artigo > margem_tempo:
                    noticias_coletadas.append(f"- {artigo.title}\nLink: {artigo.link}\n")
        except Exception:
            continue
    
    if noticias_coletadas:
        analisar_bloco_com_ia(noticias_coletadas)
    else:
        print("Nenhuma atualização nos últimos 15 min.")

if __name__ == "__main__":
    buscar_furos()
