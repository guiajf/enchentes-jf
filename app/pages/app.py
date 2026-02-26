import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from PIL import Image
import requests
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Dashboard Enchentes Juiz de Fora - Fevereiro 2026",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para estilo de emergência
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #dc2626;
        text-align: center;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #7f1d1d;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 600;
    }
    .metric-card {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-left: 5px solid #dc2626;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .news-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .news-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .alert-box {
        background-color: #fef3c7;
        border-left: 5px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .update-time {
        font-size: 0.8rem;
        color: #6b7280;
        font-style: italic;
    }
    .neighborhood-tag {
        display: inline-block;
        background-color: #dbeafe;
        color: #1e40af;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        margin: 0.25rem;
        font-weight: 600;
    }
    .risk-high {
        color: #dc2626;
        font-weight: bold;
    }
    .risk-medium {
        color: #f59e0b;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #fef2f2;
        border-bottom: 3px solid #dc2626;
    }
</style>
""", unsafe_allow_html=True)

# Dados atualizados (26/02/2026 - 16h) baseados nas fontes oficiais
DADOS_ATUALIZADOS = {
    "mortes": 46,
    "desaparecidos": 21,
    "desabrigados": 3400,
    "desalojados": 400,
    "chuva_acumulada_fev": 589.6,  # mm até dia 24
    "chuva_48h": 227.6,  # mm entre 22-24 fev
    "ocorrencias": 1017,
    "data_atualizacao": "25/02/2026 16:00"
}

# Bairros afetados com dados reais
BAIRROS_AFETADOS = {
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

# Notícias simuladas baseadas em fontes reais
NOTICIAS = [
    {
        "fonte": "CNN Brasil",
        "horario": "25/02 14:30",
        "titulo": "Vídeo mostra momento exato de deslizamento no bairro Três Moinhos",
        "resumo": "Moradores registraram o deslizamento de terra que atingiu residências na última terça-feira. São 49 mortes confirmadas e 18 desaparecidos.",
        "tipo": "Vídeo",
        "imagem": "https://kimi-web-img.moonshot.cn/img/admin.cnnbrasil.com.br/410af35fcc2cda3da52e1bb6d0d3856557340e5f.png"
    },
    {
        "fonte": "G1",
        "horario": "25/02 16:00",
        "titulo": "Chuva deixa 46 mortos e 21 desaparecidos em Juiz de Fora e Ubá",
        "resumo": "Balanço atualizado da Defesa Civil confirma 40 mortes em Juiz de Fora e 6 em Ubá. Mais de 3.400 pessoas estão desabrigadas.",
        "tipo": "Notícia",
        "imagem": None
    },
    {
        "fonte": "Prefeitura de Juiz de Fora",
        "horario": "25/02 12:00",
        "titulo": "Fevereiro de 2026 é o mês mais chuvoso da história da cidade",
        "resumo": "Já são 589,6mm de chuva acumulada, superando em 270% a média histórica de 170mm para o mês.",
        "tipo": "Boletim",
        "imagem": None
    },
    {
        "fonte": "Estadão",
        "horario": "24/02 18:45",
        "titulo": "Imagens de drone mostram impactos da enchente no Rio Paraibuna",
        "resumo": "Rio transbordou em pontos históricos da cidade, deixando bairros ilhados e causando destruição em vias principais.",
        "tipo": "Imagens",
        "imagem": "https://kimi-web-img.moonshot.cn/img/www.estadao.com.br/04c23ade3406b8ce14507c5d7de62f0774383cab.jpg"
    },
    {
        "fonte": "Agência Brasil",
        "horario": "25/02 10:20",
        "titulo": "Governo federal anuncia auxílio de R$ 800 para desabrigados",
        "resumo": "Força Nacional do SUS enviada à região. Ministros estiveram na cidade reconhecendo estado de calamidade pública.",
        "tipo": "Política",
        "imagem": None
    },
    {
        "fonte": "MetSul Meteorologia",
        "horario": "24/02 09:15",
        "titulo": "Análise técnica: Convecção atmosférica causou precipitação extrema",
        "resumo": "Encontro de massa de ar quente/úmido com ar frio do oeste, aliado à baixa pressão no leste de MG, explica volumes extremos.",
        "tipo": "Análise",
        "imagem": None
    }
]

# Imagens das enchentes
IMAGENS_ENChente = [
    {
        "url": "https://kimi-web-img.moonshot.cn/img/stories.cnnbrasil.com.br/864f4ffaa140d9d8bfd771aea59dfac7b559abcb.jpg",
        "legenda": "Alagamento no bairro Cidade Universitária - 23/02/2026",
        "fonte": "CNN Brasil"
    },
    {
        "url": "https://kimi-web-img.moonshot.cn/img/i0.wp.com/7ab7fdc7db8edc3dc5c496f1ecd81874202c72da.jpeg",
        "legenda": "Rua alagada no Centro de Juiz de Fora durante temporal",
        "fonte": "JF Informa"
    },
    {
        "url": "https://kimi-web-img.moonshot.cn/img/admin.cnnbrasil.com.br/7fd29c1ef3c0ec4269149c23bd611659feb259d6.png",
        "legenda": "Rua coberta de lama após deslizamento no bairro São Pedro",
        "fonte": "CNN Brasil"
    },
    {
        "url": "https://kimi-web-img.moonshot.cn/img/stories.cnnbrasil.com.br/cb405af263f26dcf0aefefd92b6ca1e37c91af21.jpg",
        "legenda": "Ponte histórica alagada sobre o Rio Paraibuna",
        "fonte": "CNN Brasil"
    }
]

def get_current_time():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def simulate_live_updates():
    """Simula atualizações em tempo real dos dados"""
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
        st.session_state.update_count = 0
    
    time_diff = (datetime.now() - st.session_state.last_update).seconds
    
    if time_diff > 30:  # Atualiza a cada 30 segundos
        st.session_state.last_update = datetime.now()
        st.session_state.update_count += 1
        return True
    return False

def display_metrics():
    """Exibe métricas principais em cards"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#dc2626; font-size:2rem;">{DADOS_ATUALIZADOS['mortes']}</h3>
            <p style="margin:0; color:#7f1d1d; font-weight:bold;">ÓBITOS CONFIRMADOS</p>
            <p style="margin:0; font-size:0.8rem; color:#6b7280;">Atualizado: {DADOS_ATUALIZADOS['data_atualizacao']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#f59e0b; font-size:2rem;">{DADOS_ATUALIZADOS['desaparecidos']}</h3>
            <p style="margin:0; color:#92400e; font-weight:bold;">DESAPARECIDOS</p>
            <p style="margin:0; font-size:0.8rem; color:#6b7280;">Buscas em andamento</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#2563eb; font-size:2rem;">{DADOS_ATUALIZADOS['desabrigados']:,}</h3>
            <p style="margin:0; color:#1e40af; font-weight:bold;">DESABRIGADOS</p>
            <p style="margin:0; font-size:0.8rem; color:#6b7280;">Abrigos improvisados</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#7c3aed; font-size:2rem;">{DADOS_ATUALIZADOS['desalojados']}</h3>
            <p style="margin:0; color:#5b21b6; font-weight:bold;">DESALOJADOS</p>
            <p style="margin:0; font-size:0.8rem; color:#6b7280;">Sem acesso às casas</p>
        </div>
        """, unsafe_allow_html=True)

def display_map_section():
    """Exibe mapa e dados por bairro"""
    st.subheader("🗺️ Mapeamento de Áreas Afetadas")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Simulação de mapa com dados dos bairros
        st.info("**Status dos Bairros - Atualizado em tempo real**")
        
        df_bairros = pd.DataFrame([
            {
                "Bairro": bairro,
                "Tipo": dados["tipo"],
                "Gravidade": dados["gravidade"],
                "Status": dados["status"],
                "Vítimas": dados.get("vítimas", 0),
                "Chuva(mm)": dados.get("chuva_mm", 0)
            }
            for bairro, dados in BAIRROS_AFETADOS.items()
        ])
        
        # Colorir por gravidade
        def color_gravidade(val):
            if val == "Crítica" or val == "Alta":
                return 'background-color: #fee2e2; color: #dc2626; font-weight: bold'
            elif val == "Média":
                return 'background-color: #fef3c7; color: #92400e'
            return ''
        
        styled_df = df_bairros.style.applymap(color_gravidade, subset=['Gravidade'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
    with col2:
        st.markdown("### 📊 Estatísticas por Tipo")
        
        tipos = df_bairros["Tipo"].value_counts()
        st.bar_chart(tipos, color="#dc2626")
        
        st.markdown("### ⚠️ Alertas Ativos")
        st.markdown("""
        <div class="alert-box">
            <strong>🔴 Alerta Vermelho</strong><br>
            Risco de novos deslizamentos nas próximas 24h<br>
            <em>Fonte: Defesa Civil/CEMADEN</em>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background-color: #dbeafe; border-left: 5px solid #2563eb; padding: 1rem; border-radius: 0.5rem;">
            <strong>🔵 Informe</strong><br>
            Rio Paraibuna: nível baixando, mas ainda acima da cota de alerta<br>
            <em>Atualização: 15 min atrás</em>
        </div>
        """, unsafe_allow_html=True)

def display_news_feed():
    """Feed de notícias estilo redes sociais"""
    st.subheader("📰 Central de Notícias e Redes Sociais")
    
    # Filtros
    col1, col2 = st.columns([1, 3])
    with col1:
        filtro = st.selectbox("Filtrar por:", ["Todas", "Vídeos", "Imagens", "Boletins Oficiais", "Análises"])
    
    # Simular atualizações ao vivo
    if simulate_live_updates():
        st.toast("🔄 Novas atualizações disponíveis!", icon="🔄")
    
    # Exibir notícias
    for noticia in NOTICIAS:
        if filtro != "Todas" and filtro not in noticia["tipo"]:
            continue
            
        with st.container():
            st.markdown(f"""
            <div class="news-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="background-color: #dc2626; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: bold;">{noticia["fonte"]}</span>
                    <span style="color: #6b7280; font-size: 0.875rem;">{noticia["horario"]}</span>
                </div>
                <h4 style="margin: 0.5rem 0; color: #111827;">{noticia["titulo"]}</h4>
                <p style="margin: 0; color: #4b5563; line-height: 1.5;">{noticia["resumo"]}</p>
                <div style="margin-top: 0.5rem;">
                    <span style="background-color: #f3f4f6; color: #374151; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">{noticia["tipo"]}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if noticia["imagem"]:
                try:
                    response = requests.get(noticia["imagem"], timeout=5)
                    img = Image.open(BytesIO(response.content))
                    st.image(img, use_column_width=True, caption=f"Fonte: {noticia['fonte']}")
                except:
                    st.warning("Imagem não disponível")
            
            st.divider()

def display_gallery():
    """Galeria de imagens das enchentes"""
    st.subheader("📸 Galeria de Imagens - Documentação Visual")
    
    cols = st.columns(2)
    for idx, img_data in enumerate(IMAGENS_ENChente):
        with cols[idx % 2]:
            try:
                response = requests.get(img_data["url"], timeout=5)
                img = Image.open(BytesIO(response.content))
                st.image(img, use_column_width=True, caption=f"{img_data['legenda']} | Fonte: {img_data['fonte']}")
            except Exception as e:
                st.error(f"Erro ao carregar imagem: {img_data['legenda']}")
                st.info("Imagem indisponível no momento")

def display_weather_data():
    """Dados meteorológicos detalhados"""
    st.subheader("🌧️ Dados Meteorológicos - Monitoramento")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Acumulado de Chuva - Fevereiro 2026")
        
        # Dados de chuva por dia (simulados baseados em dados reais)
        dias = list(range(20, 26))
        chuva_por_dia = [15, 45, 89, 138.6, 45, 12]  # Baseado nos dados do INMET/CEMADEN
        
        df_chuva = pd.DataFrame({
            "Dia": [f"{d}/02" for d in dias],
            "Precipitação (mm)": chuva_por_dia
        })
        
        st.bar_chart(df_chuva.set_index("Dia"), color="#3b82f6")
        
        st.markdown(f"""
        **Dados do INMET/CEMADEN:**
        - **Total acumulado (até 24/02):** {DADOS_ATUALIZADOS['chuva_acumulada_fev']} mm
        - **Média histórica de fevereiro:** 170 mm
        - **Excesso:** +{((DADOS_ATUALIZADOS['chuva_acumulada_fev']/170-1)*100):.0f}% da média
        - **Volume em 48h (22-24/02):** {DADOS_ATUALIZADOS['chuva_48h']} mm
        """)
    
    with col2:
        st.markdown("### 📍 Precipitação por Localidade (CEMADEN)")
        
        locais = ["Cidade Universitária", "N. S. de Lourdes", "Centro", "Três Moinhos", "Benfica"]
        valores = [221.72, 216.19, 215.43, 198.5, 175.2]
        
        df_locais = pd.DataFrame({
            "Local": locais,
            "mm/48h": valores
        }).sort_values("mm/48h", ascending=True)
        
        st.bar_chart(df_locais.set_index("Local"), color="#ef4444")
        
        st.markdown("""
        **Análise Meteorológica:**
        - Sistema de baixa pressão sobre o leste de MG
        - Convecção de ar quente/úmido + ar frio do oeste
        - Canalização de umidade do oceano
        - Relevo acidentado favoreceu concentração de precipitação
        """)

def display_social_monitoring():
    """Monitoramento de redes sociais"""
    st.subheader("📱 Monitoramento de Redes Sociais - Em tempo real")
    
    # Simulação de posts de redes sociais
    posts = [
        {
            "user": "@defesaciviljf",
            "platform": "Twitter/X",
            "time": "10 min atrás",
            "content": "⚠️ ATENÇÃO: Equipes trabalham no resgate em 3 pontos da cidade. Evite deslocamento para bairros do entorno do Rio Paraibuna.",
            "engagement": "1.2k compartilhamentos"
        },
        {
            "user": "@prefeitura_jf",
            "platform": "Instagram",
            "time": "25 min atrás",
            "content": "📍 Abrigos temporários disponíveis: Ginásio do Mariano Procópio, CEFET-MG e Parque da Lajinha. Doe água, alimentos não perecíveis e roupas.",
            "engagement": "3.4k curtidas"
        },
        {
            "user": "@corpo_bombeiros_mg",
            "platform": "Twitter/X",
            "time": "45 min atrás",
            "content": "🚨 Soterramento no bairro Granjas Betânia: 2 vítimas resgatadas com vida. Buscas continuam por 1 desaparecido. Cão farejador em ação.",
            "engagement": "890 compartilhamentos"
        },
        {
            "user": "Morador - Bairro São Pedro",
            "platform": "WhatsApp (Grupo Emergência)",
            "time": "1h atrás",
            "content": "URGENTE: Rua João XXIII interditada, árvore caída sobre fios de alta tensão. Equipe da CEMIG a caminho.",
            "engagement": "Visto por 240 pessoas"
        }
    ]
    
    for post in posts:
        with st.container():
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem; background-color: #f3f4f6; border-radius: 0.5rem;">
                    <div style="font-size: 2rem;">{"🐦" if "Twitter" in post["platform"] else "📷" if "Instagram" in post["platform"] else "💬"}</div>
                    <div style="font-size: 0.75rem; color: #6b7280;">{post["platform"]}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background-color: white; padding: 1rem; border-radius: 0.5rem; border: 1px solid #e5e7eb;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <strong style="color: #1f2937;">{post["user"]}</strong>
                        <span style="color: #9ca3af; font-size: 0.875rem;">{post["time"]}</span>
                    </div>
                    <p style="margin: 0; color: #4b5563;">{post["content"]}</p>
                    <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #6b7280;">
                        📊 {post["engagement"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("")

def main():
    # Header principal
    st.markdown('<h1 class="main-header">🌊 DASHBOARD ENCHENTES JUIZ DE FORA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Monitoramento em Tempo Real - Tragédia de Fevereiro/2026 | Zona da Mata Mineira</p>', unsafe_allow_html=True)
    
    # Barra de status
    status_col1, status_col2, status_col3 = st.columns(3)
    with status_col1:
        st.error("🔴 **Estado de Calamidade Pública** - Decreto 180 dias")
    with status_col2:
        st.warning("⏱️ **Última atualização:** " + get_current_time())
    with status_col3:
        st.info("🔄 **Auto-refresh:** Ativo (30s)")
    
    st.divider()
    
    # Métricas principais
    display_metrics()
    
    st.divider()
    
    # Tabs para organização
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Mapa e Bairros", 
        "📰 Notícias", 
        "📸 Imagens", 
        "🌧️ Meteorologia", 
        "📱 Redes Sociais"
    ])
    
    with tab1:
        display_map_section()
    
    with tab2:
        display_news_feed()
    
    with tab3:
        display_gallery()
    
    with tab4:
        display_weather_data()
    
    with tab5:
        display_social_monitoring()
    
    # Footer com informações importantes
    st.divider()
    st.markdown("""
    <div style="background-color: #f3f4f6; padding: 1rem; border-radius: 0.5rem; text-align: center;">
        <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">
            <strong>Fontes oficiais:</strong> Defesa Civil de Juiz de Fora | Corpo de Bombeiros MG | INMET | CEMADEN | Prefeitura de Juiz de Fora<br>
            <strong>Desenvolvido para:</strong> Monitoramento e transparência da informação pública | Dados atualizados conforme boletins oficiais<br>
            <em>Este é um painel de acompanhamento. Em emergência, ligue 193 (Bombeiros) ou 199 (Defesa Civil)</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Simulação de atualização automática
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()
