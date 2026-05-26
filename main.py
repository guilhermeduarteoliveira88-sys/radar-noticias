import feedparser
import requests
import time
import calendar
import os
from datetime import datetime, timedelta, timezone

# --- CREDENCIAIS ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

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

Fontes:
🔗 https://www.dafont.com/pt/one-1.font
🔗 https://www.dafont.com/pt/from-me-2-you.font

REGRA: Se nada for relevante, responda EXATAMENTE com a palavra: VAZIO. NUNCA utilize a tag <a href="...">, coloque APENAS a URL pura após o ícone 🔗.
"""

def enviar_telegram(mensagem):
    partes = [mensagem[i:i+4000] for i in range(0, len(mensagem), 4000)]
    for parte in partes:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': CHAT_ID, 
            'text': parte, 
            'parse_mode': 'HTML',
            'link_preview_options': {'is_disabled': True} 
        }
        resposta = requests.post(url, json=payload)
        
        if resposta.status_code != 200:
            print(f"Erro do Telegram ao enviar: {resposta.text}")
            texto_limpo = parte.replace("<b>", "").replace("</b>", "")
            payload_limpo = {
                'chat_id': CHAT_ID, 
                'text': texto_limpo,
                'link_preview_options': {'is_disabled': True} 
            }
            requests.post(url, json=payload_limpo)

def analisar_bloco_com_ia(lista_noticias):
    prompt = f"{CONTEXTO}\n\n=== NOTÍCIAS RECENTES ===\n" + "\n".join(lista_noticias)
    
    # Conexão DIRETA via URL (Bypassa bibliotecas quebradas)
    url_ia = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    dados = {
        "contents": [{"parts":[{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3}
    }
    
    try:
        resposta_ia = requests.post(url_ia, headers=headers, json=dados)
        
        if resposta_ia.status_code == 200:
            resultado_json = resposta_ia.json()
            texto_final = resultado_json['candidates'][0]['content']['parts'][0]['text'].strip()
            
            if texto_final.upper() != "VAZIO" and texto_final:
                texto_final = texto_final.replace("```html", "").replace("```", "").strip()
                enviar_telegram(texto_final)
                print("Boletim processado e enviado!")
            else:
                print("Nenhuma relevância encontrada pela IA.")
        else:
            print(f"O servidor da IA recusou a conexão: {resposta_ia.status_code} - {resposta_ia.text}")
            
    except Exception as e:
        print(f"Erro de comunicação com a IA: {e}")

def buscar_furos():
    agora = datetime.now(timezone.utc)
    margem_tempo = agora - timedelta(days=1) # Mantido 1 dia para o teste rodar agora
    noticias_coletadas = []
    
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for artigo in feed.entries:
                if not hasattr(artigo, 'published_parsed') or not artigo.published_parsed:
                    continue
                
                data_artigo = datetime.fromtimestamp(calendar.timegm(artigo.published_parsed), timezone.utc)
                
                if data_artigo > margem_tempo:
                    noticias_coletadas.append(f"- {artigo.title}\nLink: {artigo.link}\n")
        except Exception:
            continue
    
    if noticias_coletadas:
        print(f"Enviando {len(noticias_coletadas)} matérias diretamente para a API...")
        analisar_bloco_com_ia(noticias_coletadas)
    else:
        print("Nenhuma atualização recente.")

if __name__ == "__main__":
    buscar_furos()
