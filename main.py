import feedparser
import requests
import time
import os
import google.generativeai as genai
from datetime import datetime, timedelta, timezone

# --- CREDENCIAIS (Puxadas do painel de segurança do GitHub) ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Configura a IA do Google
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- FONTES DE NOTÍCIAS ---
FEEDS = [
    'https://www.poder360.com.br/feed/',
    'https://g1.globo.com/rss/g1/politica/',
    'https://www.metropoles.com/feed'
]

# --- O FILTRO DE RELEVÂNCIA (O cérebro da IA) ---
CONTEXTO = """
Você é um curador de notícias focado no cenário político e administrativo. 
Sua tarefa é avaliar se a manchete e o resumo a seguir têm impacto direto e prático para o usuário.

Foco de interesse do usuário:
1. Governo Federal (decisões, decretos, medidas econômicas e mudanças na administração).
2. Projetos políticos e leis que atinjam o cidadão diretamente (tributação, direitos trabalhistas, infraestrutura, etc).
3. Eleições (cenário nacional e local, candidatos, regras eleitorais).
4. Transporte e mobilidade urbana do Entorno do DF e ligação com Brasília.
5. Ações e decisões do Consórcio Intermunicipal do Entorno do DF.

Regras de aprovação:
- Aprove (SIM): Notícias sobre tarifas de ônibus, obras de mobilidade no DF/Entorno, decisões do Consórcio do Entorno, anúncios importantes do Governo Federal, projetos de lei com impacto real na vida do cidadão e movimentações eleitorais relevantes.
- Reprove (NÃO): Intrigas políticas vazias, troca de farpas entre políticos, fofocas de bastidores sem impacto prático, crimes comuns ou notícias de outros estados que não afetam a região do DF e Entorno.

Responda ESTRITAMENTE com a palavra SIM (se for relevante) ou NÃO (se for irrelevante). Nenhuma palavra a mais.
"""

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': mensagem, 'parse_mode': 'HTML'}
    requests.post(url, data=payload)

def avaliar_relevancia_com_ia(titulo, resumo):
    prompt = f"{CONTEXTO}\n\nTítulo: {titulo}\nResumo: {resumo}"
    try:
        resposta = model.generate_content(prompt)
        decisao = resposta.text.strip().upper() 
        return "SIM" in decisao
    except Exception:
        # Se a IA falhar (ex: instabilidade), assume False para não mandar spam
        return False

def buscar_furos():
    # Pega a hora atual e define o limite para matérias dos últimos 15 minutos
    agora = datetime.now(timezone.utc)
    margem_tempo = agora - timedelta(minutes=15)
    
    for url in FEEDS:
        feed = feedparser.parse(url)
        
        for artigo in feed.entries:
            try:
                # Converte a data do feed
                data_artigo = datetime.fromtimestamp(time.mktime(artigo.published_parsed), timezone.utc)
                
                # Só processa se for matéria muito recente
                if data_artigo > margem_tempo:
                    titulo = artigo.title
                    resumo = artigo.get('summary', '') 
                    
                    # Passa pelo filtro da IA
                    if avaliar_relevancia_com_ia(titulo, resumo):
                        msg = f"🎯 <b>Radar Relevante:</b>\n\n<b>{titulo}</b>\n\n<a href='{artigo.link}'>Ler matéria</a>"
                        enviar_telegram(msg)
            except Exception:
                continue

# Executa o código principal
if __name__ == "__main__":
    buscar_furos()
