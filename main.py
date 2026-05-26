import feedparser
import requests
import time
import os
from google import genai
from datetime import datetime, timedelta, timezone

# --- CREDENCIAIS ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

client = genai.Client(api_key=GEMINI_API_KEY)

# --- FONTES EXPANDIDAS ---
FEEDS = [
    # Portais Tradicionais
    'https://www.poder360.com.br/feed/',
    'https://g1.globo.com/rss/g1/politica/',
    'https://www.metropoles.com/feed',
    'https://noticias.uol.com.br/politica/rss.xml',
    'https://www.cartacapital.com.br/politica/feed/',
    'https://oantagonista.com.br/feed/',
    
    # Jornalistas (Furos Rápidos via Bluesky)
    'https://bsky.app/profile/andreiasadi.bsky.social/rss',
    'https://bsky.app/profile/igorgadelha.bsky.social/rss',
    'https://bsky.app/profile/octavio-guedes.bsky.social/rss',
    'https://bsky.app/profile/camilabomfim.bsky.social/rss'
]

# --- INSTRUÇÃO DE AGRUPAMENTO DA IA ---
CONTEXTO = """
Você é um curador de informações. Abaixo você receberá uma lista com TODAS as notícias e posts publicados nos últimos 15 minutos.

Seu público-alvo foca em: Governo Federal, publicidade legal, leis com impacto real, eleições, e infraestrutura/mobilidade no DF e Entorno (Consórcio Intermunicipal).

SUA TAREFA:
1. Ignore tudo que for irrelevante ou fofoca vazia.
2. Agrupe as matérias que falam sobre o MESMO ASSUNTO.
3. Crie um resumo limpo e direto agrupando as fontes.

FORMATO OBRIGATÓRIO DE SAÍDA (Use HTML):
🚨 <b>Radar Atualizado</b>

🔹 <b>[Título do Assunto]</b>
[Breve resumo do que aconteceu, sem enrolação]
🔗 <a href="link_aqui">Fonte 1</a> | <a href="link_aqui">Fonte 2</a>

(Repita o bloco acima se houver mais de um assunto diferente)

REGRA CRÍTICA: Se a lista original não tiver NENHUMA notícia relevante para o perfil, não invente nada. Responda EXATAMENTE com a palavra: VAZIO
"""

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': mensagem, 'parse_mode': 'HTML'}
    requests.post(url, data=payload)

def analisar_bloco_com_ia(lista_noticias):
    prompt = CONTEXTO + "\n\n=== NOTÍCIAS RECENTES ===\n" + "\n".join(lista_noticias)
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        texto_final = response.text.strip()
        
        # O código não envia nada se a IA julgar que tudo era inútil
        if texto_final != "VAZIO" and texto_final != "":
            # Limpa possíveis formatações de markdown que a IA possa tentar incluir
            texto_final = texto_final.replace("```html", "").replace("```", "").strip()
            enviar_telegram(texto_final)
            print("Boletim enviado com sucesso!")
        else:
            print("Nada de relevante neste ciclo.")
            
    except Exception as e:
        print(f"Erro na IA: {e}")

def buscar_furos():
    agora = datetime.now(timezone.utc)
    # Alterado para 15 minutos
    margem_tempo = agora - timedelta(minutes=15)
    
    noticias_coletadas = []
    
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for artigo in feed.entries:
                data_artigo = datetime.fromtimestamp(time.mktime(artigo.published_parsed), timezone.utc)
                
                if data_artigo > margem_tempo:
                    titulo = artigo.title
                    link = artigo.link
                    # Guarda na lista para enviar tudo de uma vez
                    noticias_coletadas.append(f"- {titulo}\nLink: {link}\n")
        except Exception:
            continue
    
    # Se achou alguma coisa nos últimos 15 min, manda o pacote pra IA julgar
    if noticias_coletadas:
        print(f"{len(noticias_coletadas)} notícias cruas encontradas. Enviando para IA agrupar...")
        analisar_bloco_com_ia(noticias_coletadas)
    else:
        print("Nenhuma matéria recente publicada nos portais nos últimos 15 minutos.")

if __name__ == "__main__":
    buscar_furos()
