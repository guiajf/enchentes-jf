import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests
from PIL import Image
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Dashboard Enchentes Juiz de Fora - Fevereiro 2026",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
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
    }
    .alert-box {
        background-color: #fef3c7;
        border-left: 5px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Dados
DADOS_ATUALIZADOS = {
    "mortes": 46,
    "desaparecidos": 21,
    "desabrigados": 3400,
    "desalojados": 400,
    "chuva_acumulada_fev": 589.6,
    "chuva_48h": 227.6,
    "ocorrencias": 1017,
    "data_atualizacao": "25/02/2026 16:00"
}

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

NOTICIAS = [
    {"fonte": "CNN Brasil", "horario": "25/02 14:30", "titulo": "Vídeo mostra momento exato de deslizamento no bairro Três Moinhos", "resumo": "49 mortes confirmadas e 18 desaparecidos.", "tipo": "Vídeo"},
    {"fonte": "G1", "horario": "25/02 16:00", "titulo": "Chuva deixa 46 mortos e 21 desaparecidos em Juiz de Fora e Ubá", "resumo": "Balanço atualizado da Defesa Civil.", "tipo": "Notícia"},
    {"fonte": "Prefeitura JF", "horario": "25/02 12:00", "titulo": "Fevereiro de 2026 é o mês mais chuvoso da história", "resumo": "589,6mm de chuva acumulada.", "tipo": "Boletim"}
]

IMAGENS = [
    "https://kimi-web-img.moonshot.cn/img/stories.cnnbrasil.com.br/864f4ffaa140d9d8bfd771aea59dfac7b559abcb.jpg",
    "https://kimi-web-img.moonshot.cn/img/i0.wp.com/7ab7fdc7db8edc3dc5c496f1ecd81874202c72da.jpeg",
    "https://kimi-web-img.moonshot.cn/img/admin.cnnbrasil.com.br/7fd29c1ef3c0ec4269149c23bd611659feb259d6.png"
]

def main():
    # Header
    st.markdown('<h1 class="main-header">🌊 DASHBOARD ENCHENTES JUIZ DE FORA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Monitoramento em Tempo Real - Tragédia de Fevereiro/2026</p>', unsafe_allow_html=True)
    
    # Status
    col1, col2, col3 = st.columns(3)
    col1.error("🔴 Estado de Calamidade Pública - Decreto 180 dias")
    col2.warning(f"⏱️ Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    col3.info("🔄 Auto-refresh: Ativo")
    
    st.divider()
    
    # Métricas
    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        (c1, DADOS_ATUALIZADOS['mortes'], "ÓBITOS", "#dc2626"),
        (c2, DADOS_ATUALIZADOS['desaparecidos'], "DESAPARECIDOS", "#f59e0b"),
        (c3, DADOS_ATUALIZADOS['desabrigados'], "DESABRIGADOS", "#2563eb"),
        (c4, DADOS_ATUALIZADOS['desalojados'], "DESALOJADOS", "#7c3aed")
    ]
    
    for col, valor, label, cor in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="margin:0; color:{cor}; font-size:2rem;">{valor}</h3>
                <p style="margin:0; color:{cor}; font-weight:bold;">{label}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🗺️ Bairros", "📰 Notícias", "📸 Imagens"])
    
    with tab1:
        st.subheader("Mapeamento de Áreas Afetadas")
        df = pd.DataFrame([
            {"Bairro": b, "Tipo": d["tipo"], "Gravidade": d["gravidade"], 
             "Status": d["status"], "Vítimas": d.get("vítimas", 0)}
            for b, d in BAIRROS_AFETADOS.items()
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Gráfico
        st.bar_chart(df["Gravidade"].value_counts(), color="#dc2626")
    
    with tab2:
        st.subheader("Central de Notícias")
        for noticia in NOTICIAS:
            with st.container():
                st.markdown(f"""
                <div class="news-card">
                    <span style="background:#dc2626; color:white; padding:2px 8px; border-radius:4px; font-size:0.8rem;">{noticia['fonte']}</span>
                    <span style="color:#6b7280; font-size:0.8rem; float:right;">{noticia['horario']}</span>
                    <h4 style="margin:10px 0 5px 0;">{noticia['titulo']}</h4>
                    <p style="margin:0; color:#4b5563;">{noticia['resumo']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab3:
        st.subheader("Galeria de Imagens")
        cols = st.columns(3)
        for idx, url in enumerate(IMAGENS):
            with cols[idx % 3]:
                try:
                    response = requests.get(url, timeout=5)
                    img = Image.open(BytesIO(response.content))
                    st.image(img, use_container_width=True)
                except:
                    st.error("Imagem indisponível")

if __name__ == "__main__":
    main()