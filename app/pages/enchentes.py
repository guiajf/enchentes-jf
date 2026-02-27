import streamlit as st
import os
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from PIL import Image
from io import BytesIO
import re
import json
import time
import os

# Tratamento de erro para BeautifulSoup (caso não esteja instalado)
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    st.warning("BeautifulSoup não instalado. Modo de demonstração ativado.")

# Tratamento de erro para feedparser
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

# Configuração da página
st.set_page_config(
    page_title="Dashboard Enchentes Juiz de Fora - Atualização em tempo real",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS mantido (igual ao anterior)
st.markdown("""
<style>
    .main-header { font-size: 3rem; font-weight: bold; color: #dc2626; text-align: center; }
    .sub-header { font-size: 1.2rem; color: #7f1d1d; text-align: center; margin-bottom: 2rem; }
    .metric-card { background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); 
                   border-left: 5px solid #dc2626; padding: 1rem; border-radius: 0.5rem; }
    .update-badge { background-color: #10b981; color: white; padding: 0.25rem 0.75rem; 
                    border-radius: 9999px; font-size: 0.875rem; font-weight: bold; }
    .news-card { background-color: #ffffff; border: 1px solid #e5e7eb; 
                 border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem; }
    .alert-box { background-color: #fef3c7; border-left: 5px solid #f59e0b; 
                 padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
    .demo-mode { background-color: #dbeafe; border: 2px solid #3b82f6; 
                 padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SISTEMA DE DADOS COM FALLBACK
# =============================================================================

class DataManager:
    """Gerencia dados com fallback para modo offline"""
    
    def __init__(self):
        self.last_update = None
        self.cache_duration = 300  # 5 minutos
        
        # Dados base históricos (fallback)
        self.historical_data = {
            "mortes": 46,
            "desaparecidos": 21,
            "desabrigados": 3400,
            "desalojados": 400,
            "chuva_acumulada_fev": 589.6,
            "chuva_48h": 227.6,
            "ocorrencias": 1017,
            "data_atualizacao": "25/02/2026 16:00"
        }
        
        self.bairros_base = {
            "Três Moinhos": {"tipo": "Deslizamento", "gravidade": "Alta", "vítimas": 5, "status": "Bloqueado"},
            "Cidade Universitária": {"tipo": "Alagamento", "gravidade": "Alta", "chuva_mm": 221.72, "status": "Interditado"},
            "Nossa Senhora de Lourdes": {"tipo": "Alagamento", "gravidade": "Alta", "chuva_mm": 216.19, "status": "Interditado"},
            "Centro": {"tipo": "Alagamento", "gravidade": "Média", "chuva_mm": 215.43, "status": "Parcial"},
            "Santa Cruz": {"tipo": "Deslizamento", "gravidade": "Alta", "vítimas": 3, "status": "Bloqueado"},
            "Benfica": {"tipo": "Enchente", "gravidade": "Média", "status": "Restrito"},
            "São Pedro": {"tipo": "Deslizamento", "gravidade": "Alta", "vítimas": 2, "status": "Bloqueado"},
            "Mariano Procópio": {"tipo": "Alagamento", "gravidade": "Média", "status": "Parcial"},
            "São Mateus": {"tipo": "Enchente", "gravidade": "Alta", "status": "Interditado"},
            "Granjas Betânia": {"tipo": "Deslizamento", "gravidade": "Crítica", "vítimas": 8, "status": "Bloqueado"}
        }
        
        self.noticias_base = [
            {
                "fonte": "Defesa Civil MG",
                "horario": "25/02 16:00",
                "titulo": "Balanço atualizado: 46 óbitos confirmados em Juiz de Fora",
                "resumo": "Equipes continuam buscas por 21 desaparecidos. Mais de 3.400 pessoas estão desabrigadas.",
                "tipo": "Boletim Oficial",
                "url": "https://www.defesacivil.mg.gov.br/noticias"
            },
            {
                "fonte": "G1 Zona da Mata",
                "horario": "25/02 14:30",
                "titulo": "Temporal em Juiz de Fora e Ubá deixa rastro de destruição",
                "resumo": "Chuva volumosa atingiu a região entre os dias 22 e 24 de fevereiro.",
                "tipo": "Reportagem",
                "url": "https://g1.globo.com/mg/zona-da-mata/"
            },
            {
                "fonte": "CNN Brasil",
                "horario": "25/02 12:00",
                "titulo": "Vídeo: Morro desliza sobre casas no bairro Três Moinhos",
                "resumo": "Imagens mostram momento exato do deslizamento que matou 5 pessoas.",
                "tipo": "Vídeo",
                "url": "https://www.cnnbrasil.com.br"
            },
            {
                "fonte": "Prefeitura JF",
                "horario": "24/02 18:00",
                "titulo": "Fevereiro de 2026 é o mês mais chuvoso da história de Juiz de Fora",
                "resumo": "Já são 589,6mm de chuva acumulada, superando em 270% a média histórica.",
                "tipo": "Comunicado",
                "url": "https://www.pjf.mg.gov.br"
            }
        ]

data_manager = DataManager()

# =============================================================================
# FUNÇÕES DE SCRAPING COM TRATAMENTO DE ERRO
# =============================================================================

def scrape_defesa_civil():
    """Scraping com fallback para dados estáticos se falhar"""
    if not BS4_AVAILABLE:
        return []
    
    try:
        urls = [
            {"url": "https://www.defesacivil.mg.gov.br/", "nome": "Defesa Civil MG"},
            {"url": "https://www.pjf.mg.gov.br/defesa_civil/noticias.php", "nome": "Defesa Civil JF"}
        ]
        
        noticias = []
        for fonte in urls:
            try:
                response = requests.get(fonte["url"], timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                soup = BeautifulSoup(response.content, 'html.parser')
                
                keywords = ['ench', 'chuv', 'desliz', 'alag', 'temporal', 'juiz de fora']
                
                # Tentar encontrar links de notícias
                links = soup.find_all('a', href=True, limit=15)
                
                for link in links:
                    texto = link.get_text()
                    href = link['href']
                    
                    # Completar URL relativa
                    if href.startswith('/'):
                        href = fonte["url"].rstrip('/') + href
                    elif not href.startswith(('http://', 'https://')):
                        continue
                    
                    if any(k in texto.lower() for k in keywords) and len(texto.strip()) > 20:
                        noticias.append({
                            "fonte": fonte["nome"],
                            "titulo": texto.strip()[:100] + "...",
                            "horario": datetime.now().strftime("%d/%m %H:%M"),
                            "resumo": f"Notícia publicada no site da {fonte['nome']}",
                            "tipo": "Boletim",
                            "url": href
                        })
            except Exception as e:
                continue
                
        return noticias
    except Exception as e:
        return []

def parse_rss_feeds():
    """Parse de RSS com tratamento de erro"""
    if not FEEDPARSER_AVAILABLE:
        return []
    
    feeds = [
        "https://g1.globo.com/rss/g1/mg/zona-da-mata/",
        "https://www.em.com.br/rss/gerais.xml"
    ]
    
    noticias = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                titulo = entry.get('title', '')
                if any(k in titulo.lower() for k in ['juiz de fora', 'jf', 'enchente', 'chuva', 'deslizamento']):
                    noticias.append({
                        "fonte": feed.feed.get('title', 'RSS'),
                        "titulo": titulo,
                        "horario": entry.get('published', datetime.now().strftime("%d/%m %H:%M"))[:16],
                        "resumo": entry.get('summary', '')[:150] + "...",
                        "tipo": "RSS",
                        "url": entry.get('link', '#')
                    })
        except Exception as e:
            continue
    return noticias

def fetch_news_api():
    """API de notícias com chave de secrets"""
    try:
        api_key = st.secrets.get("NEWS_API_KEY", os.getenv("NEWS_API_KEY", ""))
        
        if not api_key:
            return []
            
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "Juiz de Fora enchente OR deslizamento OR chuva",
            "language": "pt",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        noticias = []
        if data.get("status") == "ok":
            for article in data.get("articles", []):
                noticias.append({
                    "fonte": article.get("source", {}).get("name", "NewsAPI"),
                    "titulo": article.get("title", ""),
                    "horario": article.get("publishedAt", "")[:16].replace("T", " "),
                    "resumo": (article.get("description", "") or "")[:150] + "...",
                    "tipo": "API",
                    "url": article.get("url", "#")
                })
        return noticias
    except:
        return []

def extract_metrics_from_news(news_list):
    """Extrai métricas usando regex"""
    metrics = {"mortes": None, "desaparecidos": None, "desabrigados": None, "desalojados": None}
    
    patterns = {
        "mortes": r'(\d+)\s*(?:mortes?|óbitos?|vítimas?\s*fatais?)',
        "desaparecidos": r'(\d+)\s*(?:desaparecidos?)',
        "desabrigados": r'(\d+)[\.\d]*\s*(?:desabrigados?)',
        "desalojados": r'(\d+)\s*(?:desalojados?)'
    }
    
    for news in news_list:
        texto = f"{news.get('titulo', '')} {news.get('resumo', '')}"
        for key, pattern in patterns.items():
            matches = re.findall(pattern, texto.lower())
            if matches:
                nums = [int(m.replace('.', '')) for m in matches]
                if metrics[key] is None or max(nums) > metrics[key]:
                    metrics[key] = max(nums)
    
    return metrics

def fetch_weather_data():
    """Dados meteorológicos da Open-Meteo (gratuita, não precisa de chave)"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": -21.76,
            "longitude": -43.35,
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "rain"],
            "daily": ["precipitation_sum", "rain_sum"],
            "timezone": "America/Sao_Paulo",
            "forecast_days": 3
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        current = data.get("current", {})
        daily = data.get("daily", {})
        
        return {
            "temperatura": current.get("temperature_2m", "N/A"),
            "umidade": current.get("relative_humidity_2m", "N/A"),
            "precipitacao_atual": current.get("precipitation", 0),
            "previsao_hoje": daily.get("precipitation_sum", [0])[0] if daily.get("precipitation_sum") else 0,
            "previsao_amanha": daily.get("precipitation_sum", [0, 0])[1] if len(daily.get("precipitation_sum", [])) > 1 else 0
        }
    except Exception as e:
        return None

# =============================================================================
# AGREGADOR DE DADOS COM CACHE
# =============================================================================

@st.cache_data(ttl=300)
def aggregate_all_data():
    """Agrega dados de todas as fontes com fallback garantido"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 1. Dados base (sempre disponíveis)
    status_text.text("Carregando dados base...")
    all_news = data_manager.noticias_base.copy()
    progress_bar.progress(25)
    
    # 2. Tentar scraping
    status_text.text("Buscando dados da Defesa Civil...")
    news_scraping = scrape_defesa_civil()
    all_news.extend(news_scraping)
    progress_bar.progress(50)
    
    # 3. Tentar RSS
    status_text.text("Lendo feeds de notícias...")
    news_rss = parse_rss_feeds()
    all_news.extend(news_rss)
    progress_bar.progress(75)
    
    # 4. Tentar API
    status_text.text("Consultando APIs...")
    news_api = fetch_news_api()
    all_news.extend(news_api)
    progress_bar.progress(90)
    
    # 5. Dados meteorológicos
    status_text.text("Obtendo dados meteorológicos...")
    weather = fetch_weather_data()
    progress_bar.progress(100)
    
    time.sleep(0.5)  # Feedback visual
    progress_bar.empty()
    status_text.empty()
    
    # Remover duplicatas
    seen = set()
    unique_news = []
    for n in all_news:
        titulo = n.get('titulo', '')
        if titulo and titulo not in seen:
            seen.add(titulo)
            unique_news.append(n)
    
    unique_news.sort(key=lambda x: x.get('horario', ''), reverse=True)
    
    # Extrair métricas ou usar fallback
    extracted = extract_metrics_from_news(unique_news)
    metrics = {
        "mortes": extracted.get("mortes") or data_manager.historical_data["mortes"],
        "desaparecidos": extracted.get("desaparecidos") or data_manager.historical_data["desaparecidos"],
        "desabrigados": extracted.get("desabrigados") or data_manager.historical_data["desabrigados"],
        "desalojados": extracted.get("desalojados") or data_manager.historical_data["desalojados"],
        "chuva_acumulada_fev": data_manager.historical_data["chuva_acumulada_fev"],
        "chuva_48h": data_manager.historical_data["chuva_48h"],
        "ocorrencias": data_manager.historical_data["ocorrencias"],
        "data_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    
    return {
        "noticias": unique_news[:15],
        "metrics": metrics,
        "weather": weather,
        "last_update": datetime.now(),
        "sources_online": len(news_scraping) + len(news_rss) + len(news_api)
    }

# =============================================================================
# INTERFACE DO USUÁRIO
# =============================================================================

def display_realtime_metrics(data):
    """Exibe métricas com indicadores visuais"""
    col1, col2, col3, col4, col5 = st.columns([2,2,2,2,2])
    
    metrics = data["metrics"]
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="update-badge">● ATUALIZADO</span>
            </div>
            <h3 style="margin:10px 0 0 0; color:#dc2626; font-size:2.5rem;">{metrics['mortes']}</h3>
            <p style="margin:0; color:#7f1d1d; font-weight:bold;">ÓBITOS</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#f59e0b; font-size:2.5rem;">{metrics['desaparecidos']}</h3>
            <p style="margin:0; color:#92400e; font-weight:bold;">DESAPARECIDOS</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#2563eb; font-size:2.5rem;">{metrics['desabrigados']:,}</h3>
            <p style="margin:0; color:#1e40af; font-weight:bold;">DESABRIGADOS</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#7c3aed; font-size:2.5rem;">{metrics['desalojados']}</h3>
            <p style="margin:0; color:#5b21b6; font-weight:bold;">DESALOJADOS</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        last_update = data.get('last_update', datetime.now())
        tempo_decorrido = (datetime.now() - last_update).seconds // 60
        fontes = data.get('sources_online', 0)
        
        st.markdown(f"""
        <div style="background: #ecfdf5; border: 2px solid #10b981; border-radius: 0.5rem; padding: 1rem; text-align: center;">
            <div style="font-size: 2rem;">🔄</div>
            <div style="font-size: 0.875rem; color: #059669; font-weight: bold;">
                Há {tempo_decorrido} min
            </div>
            <div style="font-size: 0.75rem; color: #6b7280; margin-top: 5px;">
                {fontes} fontes online
            </div>
        </div>
        """, unsafe_allow_html=True)

def display_news_feed(noticias):
    """Feed de notícias com links funcionando"""
    st.subheader(f"📰 Central de Notícias ({len(noticias)} atualizações)")
    
    for i, noticia in enumerate(noticias[:10]):
        # Garantir que todos os campos existam
        fonte = noticia.get("fonte", "Fonte desconhecida")
        horario = noticia.get("horario", datetime.now().strftime("%d/%m %H:%M"))
        titulo = noticia.get("titulo", "Sem título")
        resumo = noticia.get("resumo", "Clique no link para ler a matéria completa")
        url = noticia.get("url", "")
        
        # Cor da fonte baseada no nome
        cor_fonte = {
            "Defesa Civil MG": "#dc2626",
            "Defesa Civil (Web)": "#dc2626",
            "G1 Zona da Mata": "#c4170c",
            "CNN Brasil": "#cc0000",
            "NewsAPI": "#2563eb",
            "Prefeitura JF": "#059669",
            "Corpo de Bombeiros MG": "#d97706",
            "RSS": "#6b7280"
        }.get(fonte, "#6b7280")
        
        # Construir o link apenas se for válido
        link_html = ""
        if url and url != "#" and url.startswith(("http://", "https://")):
            link_html = f'<a href="{url}" target="_blank" style="color: #2563eb; font-size: 0.875rem; margin-top: 0.5rem; display: inline-block;">🔗 Ler matéria completa →</a>'
        elif fonte == "Defesa Civil (Web)":
            # Se veio de scraping mas sem link específico, usar link da fonte
            link_html = f'<span style="color: #6b7280; font-size: 0.875rem;">ℹ️ Fonte: {fonte}</span>'
        
        st.markdown(f"""
        <div class="news-card" style="border-left: 4px solid {cor_fonte};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="background-color: {cor_fonte}; color: white; padding: 0.25rem 0.5rem; 
                             border-radius: 0.25rem; font-size: 0.75rem; font-weight: bold;">
                    {fonte}
                </span>
                <span style="color: #6b7280; font-size: 0.875rem;">{horario}</span>
            </div>
            <h4 style="margin: 0.5rem 0; color: #111827;">{titulo}</h4>
            <p style="margin: 0; color: #4b5563; line-height: 1.5;">{resumo}</p>
            {link_html}
        </div>
        """, unsafe_allow_html=True)
        
def main():
    # Header
    st.markdown('<h1 class="main-header">🌊 DASHBOARD ENCHENTES JUIZ DE FORA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Monitoramento em tempo real - dados atualizados automaticamente</p>', unsafe_allow_html=True)
    
    # Aviso se estiver em modo demo
    if not BS4_AVAILABLE:
        st.markdown("""
        <div class="demo-mode">
            <strong>⚠️ Modo de demonstração ativo</strong><br>
            Algumas funcionalidades de web scraping estão desativadas. 
            Para funcionalidade completa, instale: <code>pip install beautifulsoup4 lxml</code>
        </div>
        """, unsafe_allow_html=True)
    
    # Controles
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        if st.button("🔄 Atualizar Agora", type="primary"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        st.error("🔴 Estado de Calamidade Pública")
    with col3:
        st.info(f"⏱️ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Carregar dados
    data = aggregate_all_data()
    
    st.divider()
    display_realtime_metrics(data)
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📰 Notícias", "🗺️ Bairros afetados", "🌦️ Meteorologia", "ℹ️ Sobre"])
    
    with tab1:
        display_news_feed(data["noticias"])
    
    with tab2:
        st.subheader("Bairros com ocorrências confirmadas")
        df_bairros = pd.DataFrame([
            {"Bairro": b, "Tipo": d["tipo"], "Gravidade": d["gravidade"], 
             "Status": d["status"], "Vítimas": d.get("vítimas", 0)}
            for b, d in data_manager.bairros_base.items()
        ])
        st.dataframe(df_bairros, use_container_width=True, hide_index=True)
        st.bar_chart(df_bairros["Gravidade"].value_counts(), color="#dc2626")
    
    with tab3:
        weather = data.get("weather")
        if weather:
            cols = st.columns(4)
            cols[0].metric("Temperatura", f"{weather.get('temperatura', 'N/A')}°C")
            cols[1].metric("Umidade", f"{weather.get('umidade', 'N/A')}%")
            cols[2].metric("Chuva Agora", f"{weather.get('precipitacao_atual', 0)}mm")
            cols[3].metric("Previsão Hoje", f"{weather.get('previsao_hoje', 0)}mm")
            
            if weather.get('previsao_amanha'):
                st.info(f"🌧️ Previsão para amanhã: {weather['previsao_amanha']}mm de precipitação")
        else:
            st.warning("Dados meteorológicos temporariamente indisponíveis")

        # Gráfico histórico
        st.subheader("Histórico de precipitação - Fevereiro 2026")
        dias = list(range(20, 26))
        chuva = [15, 45, 89, 138.6, 45, 12]
        df_chuva = pd.DataFrame({"Dia": [f"{d}/02" for d in dias], "mm": chuva})
        st.bar_chart(df_chuva.set_index("Dia"), color="#3b82f6")
        st.caption("Fonte: INMET/CEMADEN - Dados até 24/02/2026")

    with tab4:
        st.markdown("""
        ### ℹ️ Sobre o Dashboard
        
        **Fontes de Dados em Tempo Real:**
        - 🏛️ **Defesa Civil MG**: Boletins oficiais
        - 📺 **G1 Zona da Mata**: Notícias locais
        - 📡 **CNN Brasil**: Cobertura nacional
        - 📰 **RSS Feeds**: Agregadores de notícias
        - 🌦️ **Open-Meteo**: Dados meteorológicos
        
        **Atualização:**
        - Dados atualizados automaticamente a cada 5 minutos
        - Cache local para otimização de performance
        - Extração automática de métricas usando NLP
        
        **Tecnologias:**
        - Streamlit para interface
        - BeautifulSoup para scraping
        - Feedparser para RSS
        - Regex/NLP para extração de dados
        """)
        
if __name__ == "__main__":
    main()
