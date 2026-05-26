import os
import requests
import feedparser
import google.generativeai as genai

# ==========================================
# CONFIGURAÇÕES DE API E TELEGRAM
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("ID_DO_CHAT")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# FONTES DE DADOS (FEEDS RSS)
# ==========================================
RSS_FEEDS = [
    "https://feeds.folha.uol.com.br/poder/rss091.xml",
    "https://www.poder360.com.br/feed/",
    "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
    "https://www.metropoles.com/feed"
]

GOOGLE_TRENDS_BR_RSS = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=BR"

def buscar_noticias():
    """Busca as últimas notícias dos feeds RSS."""
    noticias_brutas = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            # Pega as 10 notícias mais recentes de cada portal
            for entry in feed.entries[:10]:
                noticias_brutas.append(f"- {entry.title} (Link: {entry.link})")
        except Exception as e:
            print(f"Erro ao ler o feed {url}: {e}")
    return "\n".join(noticias_brutas)

def buscar_trends():
    """Busca o Top 3 do Google Trends via RSS para evitar bloqueio de IP."""
    trends = []
    try:
        feed = feedparser.parse(GOOGLE_TRENDS_BR_RSS)
        for entry in feed.entries[:3]:
            termo = entry.title
            # O Google Trends envia o tráfego aproximado nesta tag específica
            trafego = entry.get('ht_approxtraffic', 'Alta nas buscas')
            trends.append(f"* **{termo}** ({trafego})")
    except Exception as e:
        print(f"Erro ao buscar Google Trends: {e}")
        return "Não foi possível carregar as tendências hoje."
    
    return "\n".join(trends)

def curadoria_com_ia(noticias_brutas):
    """Envia as notícias brutas para o Gemini fazer a curadoria com o seu prompt."""
    prompt = f"""
    Você é um curador sênior de notícias focado em análise de conjuntura. 
    Sua função é ler as manchetes abaixo e selecionar APENAS as 4 mais relevantes do dia.
    
    CRITÉRIOS ESTREITOS:
    1. BASTIDORES POLÍTICOS: Articulações no Congresso, tensões entre poderes e colunas de análise.
    2. ECONOMIA E TRABALHO: Projetos com impacto real no mercado (ex: Escala 6x1).
    3. DADOS E MERCADO: Estatísticas nacionais pesadas e regulações (Anvisa, quebras de patente).
    4. INOVAÇÃO NO DF: Eventos de tecnologia, publicidade, design e economia criativa em Brasília.

    FORMATO OBRIGATÓRIO DE SAÍDA:
    [Número]. [CATEGORIA]: **[Título da Notícia]**
    * *Análise:* [1 linha de resumo analítico profundo]
    🔗 [Link da notícia]
    
    Manchetes de hoje:
    {noticias_brutas}
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    resposta = model.generate_content(prompt)
    return resposta.text

def enviar_telegram(mensagem):
    """Envia a mensagem final formatada para o seu Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True # Evita que os links gerem miniaturas gigantes
    }
    resposta = requests.post(url, json=payload)
    if resposta.status_code != 200:
        print(f"Erro no Telegram: {resposta.text}")
    else:
        print("Mensagem enviada com sucesso ao Telegram!")

def main():
    print("Buscando notícias...")
    noticias = buscar_noticias()
    
    print("Filtrando com Inteligência Artificial...")
    noticias_curadas = curadoria_com_ia(noticias)
    
    print("Buscando Google Trends...")
    trends = buscar_trends()
    
    # Monta a mensagem final no layout
    mensagem_final = f"🚨 **Radar Relevante | Edição Atualizada**\n\n"
    mensagem_final += f"{noticias_curadas}\n\n"
    mensagem_final += f"---\n📈 **Top Palavras do Google**\n\n"
    mensagem_final += trends
    
    print("Enviando para o Telegram...")
    enviar_telegram(mensagem_final)
    print("Feito!")

if __name__ == "__main__":
    main()
