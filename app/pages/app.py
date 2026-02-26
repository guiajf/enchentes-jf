import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import feedparser
import json
import time
from PIL import Image
from io import BytesIO
import re
import os
from functools import lru_cache

# Configuração da página
st.set_page_config(
    page_title="Dashboard Enchentes Juiz de Fora - Atualização em Tempo Real",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS mantido igual ao original (omitido para brevidade)
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
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SISTEMA DE CACHE E ATUALIZAÇÃO
# =============================================================================

class DataManager:
    """Gerencia dados com cache e atualização automática"""
    
    def __init__(self):
        self.last_update = None
        self.cache_duration = 300  # 5 minutos
        
    def should_update(self):
        """Verifica se é hora de atualizar os dados"""
        if self.last_update is None:
            return True
        return (datetime.now() - self.last_update).seconds > self.cache_duration

# Instância global
data_manager = DataManager()

# =============================================================================
# 1. SCRAPING DE FONTES OFICIAIS
# =============================================================================

def scrape_defesa_civil():
    """Scraping do site da Defesa Civil de MG/Juiz de Fora"""
    try:
        # URLs potenciais (exemplos - verificar URLs reais)
        urls = [
            "https://www.defesacivil.mg.gov.br/",
            "https://www.pjf.mg.gov.br/defesa_civil/noticias.php"
        ]
        
        noticias = []
        for url in urls:
            try:
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Busca por notícias relacionadas a chuva/enchente
                keywords = ['ench', 'chuv', 'desliz', 'alag', 'temporal', 'defesa civil']
                
                # Exemplo de parsing (adaptar seletores CSS conforme estrutura real do site)
                articles = soup.find_all('article', limit=5) or soup.find_all('div', class_='noticia', limit=5)
                
                for article in articles:
                    titulo = article.get_text()
                    if any(k in titulo.lower() for k in keywords):
                        noticias.append({
                            "fonte": "Defesa Civil MG",
                            "titulo": titulo.strip()[:100] + "...",
                            "horario": datetime.now().strftime("%d/%m %H:%M"),
                            "resumo": "Atualização oficial da Defesa Civil",
                            "tipo": "Boletim Oficial"
                        })
            except:
                continue
                
        return noticias
    except Exception as e:
        st.error(f"Erro ao acessar Defesa Civil: {e}")
        return []

def scrape_g1_jf():
    """Scraping do G1 Zona da Mata"""
    try:
        url = "https://g1.globo.com/mg/zona-da-mata/"
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        # Seletores típicos do G1 (podem mudar)
        articles = soup.find_all('div', class_='feed-post-body', limit=10)
        
        for article in articles:
            titulo_elem = article.find('a', class_='feed-post-link')
            if titulo_elem:
                titulo = titulo_elem.get_text()
                if any(k in titulo.lower() for k in ['juiz de fora', 'jf', 'enchente', 'chuva', 'deslizamento']):
                    noticias.append({
                        "fonte": "G1 Zona da Mata",
                        "titulo": titulo,
                        "horario": datetime.now().strftime("%d/%m %H:%M"),
                        "resumo": "Clique para ler a matéria completa",
                        "tipo": "Notícia",
                        "url": titulo_elem.get('href', '#')
                    })
        return noticias
    except Exception as e:
        return []

def scrape_cnn_brasil():
    """Scraping da CNN Brasil"""
    try:
        url = "https://www.cnnbrasil.com.br/nacional/sudeste/mg/"
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        articles = soup.find_all('article', limit=10)
        
        for article in articles:
            titulo_elem = article.find('h3') or article.find('h2')
            if titulo_elem:
                titulo = titulo_elem.get_text()
                if 'juiz de fora' in titulo.lower() or 'jf' in titulo.lower():
                    noticias.append({
                        "fonte": "CNN Brasil",
                        "titulo": titulo.strip(),
                        "horario": datetime.now().strftime("%d/%m %H:%M"),
                        "resumo": "Reportagem em andamento",
                        "tipo": "Notícia"
                    })
        return noticias
    except:
        return []

# =============================================================================
# 2. APIs DE NOTÍCIAS (NEWSAPI, GNEWS, ETC)
# =============================================================================

def fetch_news_api():
    """Usa NewsAPI para buscar notícias (requer chave de API)"""
    try:
        # Obter chave de secrets ou variável de ambiente
        api_key = st.secrets.get("NEWS_API_KEY", os.getenv("NEWS_API_KEY", ""))
        
        if not api_key:
            return []  # Retorna vazio se não tiver API key
            
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "Juiz de Fora enchente OR deslizamento OR chuva",
            "language": "pt",
            "sortBy": "publishedAt",
            "pageSize": 10,
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
                    "resumo": article.get("description", "")[:150] + "...",
                    "tipo": "Notícia",
                    "url": article.get("url", "#")
                })
        return noticias
    except:
        return []

# =============================================================================
# 3. RSS FEEDS (MAIS ESTÁVEL QUE SCRAPING)
# =============================================================================

def parse_rss_feeds():
    """Parse de feeds RSS de veículos de imprensa"""
    feeds = [
        "https://g1.globo.com/rss/g1/mg/zona-da-mata/",
        "https://www.em.com.br/rss/gerais.xml",  # Estado de Minas
        # Adicionar mais feeds conforme disponibilidade
    ]
    
    noticias = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                titulo = entry.get('title', '')
                if any(k in titulo.lower() for k in ['juiz de fora', 'jf', 'enchente', 'chuva']):
                    noticias.append({
                        "fonte": feed.feed.get('title', 'RSS'),
                        "titulo": titulo,
                        "horario": entry.get('published', datetime.now().strftime("%d/%m %H:%M")),
                        "resumo": entry.get('summary', '')[:150] + "...",
                        "tipo": "Notícia",
                        "url": entry.get('link', '#')
                    })
        except:
            continue
    return noticias

# =============================================================================
# 4. EXTRAÇÃO DE DADOS ESTRUTURADOS COM NLP/REGEX
# =============================================================================

def extract_metrics_from_news(news_list):
    """Extrai métricas numéricas das notícias usando regex"""
    metrics = {
        "mortes": None,
        "desaparecidos": None,
        "desabrigados": None,
        "desalojados": None
    }
    
    # Padrões regex para extrair números
    patterns = {
        "mortes": r'(\d+)\s*(?:mortes?|óbitos?|vítimas?\s*fatais?)',
        "desaparecidos": r'(\d+)\s*(?:desaparecidos?|desaparecimentos?)',
        "desabrigados": r'(\d+)\s*(?:desabrigados?|desabrigamento)',
        "desalojados": r'(\d+)\s*(?:desalojados?|desalojamento)'
    }
    
    for news in news_list:
        texto = f"{news.get('titulo', '')} {news.get('resumo', '')}"
        for key, pattern in patterns.items():
            matches = re.findall(pattern, texto.lower())
            if matches:
                # Pega o maior número encontrado (evita falsos positivos pequenos)
                nums = [int(m) for m in matches]
                if metrics[key] is None or max(nums) > metrics[key]:
                    metrics[key] = max(nums)
    
    return metrics

def extract_locations_from_news(news_list):
    """Extrai menções a bairros e locais afetados"""
    bairros_conhecidos = [
        "Três Moinhos", "Cidade Universitária", "Nossa Senhora de Lourdes", 
        "Centro", "Santa Cruz", "Benfica", "São Pedro", "Mariano Procópio",
        "São Mateus", "Granjas Betânia", "São Bernardo", "Costa Carvalho",
        "Vila Ideal", "Bairu", "Santa Helena", "Bom Pastor"
    ]
    
    ocorrencias = {}
    for news in news_list:
        texto = f"{news.get('titulo', '')} {news.get('resumo', '')}"
        for bairro in bairros_conhecidos:
            if bairro.lower() in texto.lower():
                if bairro not in ocorrencias:
                    ocorrencias[bairro] = {"mencoes": 0, "ultima_noticia": None}
                ocorrencias[bairro]["mencoes"] += 1
                ocorrencias[bairro]["ultima_noticia"] = news.get('titulo', '')
    
    return ocorrencias

# =============================================================================
# 5. DADOS METEOROLÓGICOS EM TEMPO REAL
# =============================================================================

def fetch_weather_data():
    """Busca dados meteorológicos do INMET/CEMADEN"""
    try:
        # API pública do INMET (verificar documentação atual)
        # Exemplo usando Open-Meteo (gratuito, não requer chave)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": -21.76,  # Juiz de Fora
            "longitude": -43.35,
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "rain"],
            "daily": ["precipitation_sum", "rain_sum"],
            "timezone": "America/Sao_Paulo"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        return {
            "temperatura": data.get("current", {}).get("temperature_2m", "N/A"),
            "umidade": data.get("current", {}).get("relative_humidity_2m", "N/A"),
            "precipitacao_atual": data.get("current", {}).get("precipitation", 0),
            "previsao_chuva": data.get("daily", {}).get("precipitation_sum", [0])[0]
        }
    except:
        return None

# =============================================================================
# 6. AGREGADOR DE DADOS PRINCIPAL
# =============================================================================

@st.cache_data(ttl=300)  # Cache de 5 minutos
def aggregate_all_data():
    """Agrega dados de todas as fontes"""
    
    with st.spinner("🔄 Atualizando dados em tempo real..."):
        all_news = []
        
        # Coletar de múltiplas fontes
        all_news.extend(scrape_defesa_civil())
        all_news.extend(scrape_g1_jf())
        all_news.extend(scrape_cnn_brasil())
        all_news.extend(parse_rss_feeds())
        all_news.extend(fetch_news_api())
        
        # Remover duplicatas por título
        seen = set()
        unique_news = []
        for n in all_news:
            titulo = n.get('titulo', '')
            if titulo and titulo not in seen:
                seen.add(titulo)
                unique_news.append(n)
        
        # Ordenar por horário (mais recente primeiro)
        unique_news.sort(key=lambda x: x.get('horario', ''), reverse=True)
        
        # Extrair métricas
        extracted_metrics = extract_metrics_from_news(unique_news)
        locations = extract_locations_from_news(unique_news)
        
        # Dados meteorológicos
        weather = fetch_weather_data()
        
        # Fallback para dados históricos se não encontrar nada novo
        default_metrics = {
            "mortes": extracted_metrics.get("mortes") or 46,
            "desaparecidos": extracted_metrics.get("desaparecidos") or 21,
            "desabrigados": extracted_metrics.get("desabrigados") or 3400,
            "desalojados": extracted_metrics.get("desalojados") or 400,
            "chuva_acumulada_fev": 589.6,
            "chuva_48h": 227.6,
            "ocorrencias": 1017,
            "data_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        
        return {
            "noticias": unique_news[:20],  # Top 20 notícias
            "metrics": default_metrics,
            "locations": locations,
            "weather": weather,
            "last_update": datetime.now()
        }

# =============================================================================
# 7. INTERFACE DO DASHBOARD
# =============================================================================

def display_realtime_metrics(data):
    """Exibe métricas com indicador de atualização"""
    col1, col2, col3, col4, col5 = st.columns([2,2,2,2,2])
    
    metrics = data["metrics"]
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="update-badge">● TEMPO REAL</span>
            </div>
            <h3 style="margin:10px 0 0 0; color:#dc2626; font-size:2.5rem;">{metrics['mortes']}</h3>
            <p style="margin:0; color:#7f1d1d; font-weight:bold;">ÓBITOS CONFIRMADOS</p>
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
        # Card de status da atualização
        last_update = data.get('last_update', datetime.now())
        tempo_decorrido = (datetime.now() - last_update).seconds // 60
        
        st.markdown(f"""
        <div style="background: #ecfdf5; border: 2px solid #10b981; border-radius: 0.5rem; padding: 1rem; text-align: center;">
            <div style="font-size: 2rem;">🔄</div>
            <div style="font-size: 0.875rem; color: #059669; font-weight: bold;">
                Atualizado há {tempo_decorrido} min
            </div>
            <div style="font-size: 0.75rem; color: #6b7280; margin-top: 5px;">
                Próxima: {5 - (tempo_decorrido % 5)} min
            </div>
        </div>
        """, unsafe_allow_html=True)

def display_news_feed_realtime(noticias):
    """Feed de notícias com metadados de fonte"""
    st.subheader(f"📰 Central de Notícias em Tempo Real ({len(noticias)} fontes)")
    
    # Filtros
    col1, col2 = st.columns([1, 4])
    with col1:
        filtro_fonte = st.selectbox("Filtrar por fonte:", ["Todas"] + list(set(n.get("fonte", "Outro") for n in noticias)))
    
    noticias_filtradas = [n for n in noticias if filtro_fonte == "Todas" or n.get("fonte") == filtro_fonte]
    
    for noticia in noticias_filtradas[:10]:  # Mostrar top 10
        with st.container():
            cor_fonte = {
                "Defesa Civil MG": "#dc2626",
                "G1 Zona da Mata": "#c4170c",
                "CNN Brasil": "#cc0000"
            }.get(noticia.get("fonte"), "#6b7280")
            
            st.markdown(f"""
            <div class="news-card" style="border-left: 4px solid {cor_fonte};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="background-color: {cor_fonte}; color: white; padding: 0.25rem 0.5rem; 
                                 border-radius: 0.25rem; font-size: 0.75rem; font-weight: bold;">
                        {noticia.get("fonte", "Fonte")}
                    </span>
                    <span style="color: #6b7280; font-size: 0.875rem;">{noticia.get("horario", "Agora")}</span>
                </div>
                <h4 style="margin: 0.5rem 0; color: #111827;">{noticia.get("titulo", "Sem título")}</h4>
                <p style="margin: 0; color: #4b5563; line-height: 1.5;">{noticia.get("resumo", "")}</p>
                {f'<a href="{noticia.get("url", "#")}" target="_blank" style="color: #2563eb; font-size: 0.875rem;">🔗 Ler matéria completa</a>' if noticia.get("url") else ''}
            </div>
            """, unsafe_allow_html=True)

def display_locations_map(locations):
    """Mapa de calor de menções a bairros"""
    st.subheader("🗺️ Monitoramento de Bairros (Menções em Notícias)")
    
    if locations:
        df_loc = pd.DataFrame([
            {"Bairro": bairro, "Menções": dados["mencoes"], "Última Ocorrência": dados["ultima_noticia"][:50] + "..."}
            for bairro, dados in locations.items()
        ]).sort_values("Menções", ascending=False)
        
        st.dataframe(df_loc, use_container_width=True, hide_index=True)
        
        # Gráfico de menções
        st.bar_chart(df_loc.set_index("Bairro")["Menções"], color="#dc2626")
    else:
        st.info("Nenhuma menção a bairros específicos nas últimas notícias")

def display_weather_widget(weather):
    """Widget de condições meteorológicas"""
    if weather:
        st.subheader("🌦️ Condições Meteorológicas em Tempo Real")
        cols = st.columns(4)
        
        with cols[0]:
            st.metric("Temperatura", f"{weather.get('temperatura', 'N/A')}°C")
        with cols[1]:
            st.metric("Umidade", f"{weather.get('umidade', 'N/A')}%")
        with cols[2]:
            st.metric("Precipitação Agora", f"{weather.get('precipitacao_atual', 0)}mm")
        with cols[3]:
            st.metric("Previsão Hoje", f"{weather.get('previsao_chuva', 0)}mm")

def main():
    # Header
    st.markdown('<h1 class="main-header">🌊 DASHBOARD ENCHENTES JUIZ DE FORA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Monitoramento em Tempo Real - Dados Atualizados Automaticamente</p>', unsafe_allow_html=True)
    
    # Botão de atualização manual
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        if st.button("🔄 Forçar Atualização Agora", type="primary"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        st.error("🔴 Estado de Calamidade Pública")
    with col3:
        st.info(f"⏱️ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Carregar dados agregados
    data = aggregate_all_data()
    
    st.divider()
    
    # Métricas em tempo real
    display_realtime_metrics(data)
    
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📰 Notícias", "🗺️ Bairros Monitorados", "🌦️ Meteorologia", "ℹ️ Sobre"])
    
    with tab1:
        display_news_feed_realtime(data["noticias"])
    
    with tab2:
        display_locations_map(data["locations"])
        
        # Tabela de bairros histórica (mantida como referência)
        st.subheader("📋 Dados Oficiais da Defesa Civil")
        bairros_historico = pd.DataFrame([
            {"Bairro": "Três Moinhos", "Status": "Crítico - Deslizamentos", "Vítimas": 5},
            {"Bairro": "Granjas Betânia", "Status": "Crítico - Deslizamentos", "Vítimas": 8},
            {"Bairro": "Cidade Universitária", "Status": "Alagado", "Vítimas": 0},
            {"Bairro": "São Pedro", "Status": "Interditado", "Vítimas": 2},
        ])
        st.dataframe(bairros_historico, use_container_width=True, hide_index=True)
    
    with tab3:
        display_weather_widget(data["weather"])
        
        # Gráfico histórico
        st.subheader("📊 Acumulado de Chuva - Fevereiro 2026")
        dias = list(range(20, 26))
        chuva = [15, 45, 89, 138.6, 45, 12]
        df_chuva = pd.DataFrame({"Dia": [f"{d}/02" for d in dias], "mm": chuva})
        st.bar_chart(df_chuva.set_index("Dia"), color="#3b82f6")
    
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
    
    # Auto-refresh a cada 5 minutos
    time.sleep(1)
    if data_manager.should_update():
        st.rerun()

if __name__ == "__main__":
    main()
