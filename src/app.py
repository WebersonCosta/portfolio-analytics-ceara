# src/app.py

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Garante que a pasta src esteja no path para importação dos módulos locais
src_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(src_dir))

from config import *
from etl import (
    carrega_bases,
    normaliza_bases,
    enriquece_veiculos,
    enriquece_locados,
    deduplica_os,
    enriquece_manutencoes,
    carrega_de_para_ibge
)
from quarentena import aplica_quarentena

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Auditoria de Frota Municipal",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Carregamento de Dados com Cache ───────────────────────────────────────────
@st.cache_data
def load_all_data():
    """Executa o pipeline completo de ETL e Triagem."""
    df_vei, df_man_raw, df_loc, df_ced = carrega_bases()
    df_vei, df_man_raw, df_loc = normaliza_bases(df_vei, df_man_raw, df_loc)

    # Acoplar dados extras a base de veículos para o enriquece_veiculos
    colunas_extra = ['cd_renavam_vm', 'dt_inclusao_vd', 'dt_baixa_vbd', 'finalidade_vei']
    colunas_existentes = [c for c in colunas_extra if c in df_man_raw.columns]
    df_dados_extras = df_man_raw[colunas_existentes].drop_duplicates('cd_renavam_vm')
    df_vei = df_vei.merge(df_dados_extras, on='cd_renavam_vm', how='left')

    df_vei = enriquece_veiculos(df_vei, ANO)
    df_loc = enriquece_locados(df_loc)
    
    df_man_os = deduplica_os(df_man_raw)
    df_man_os = enriquece_manutencoes(df_man_os)

    # Aplicação da quarentena
    df_valido, df_invest, df_qr, ne_qr, ne_invest = aplica_quarentena(df_man_os)

    # Mapeamento do de-para IBGE
    df_ibge = carrega_de_para_ibge()

    return df_vei, df_valido, df_invest, df_qr, ne_qr, ne_invest, df_loc, df_ibge

# Carregando as bases de dados
try:
    df_veiculos, df_manut_os, df_invest, df_qr, ne_qr, ne_invest, df_locados, df_ibge = load_all_data()
    data_loaded_successfully = True
except Exception as e:
    st.error(f"Erro ao carregar o pipeline de dados: {e}")
    data_loaded_successfully = False

if data_loaded_successfully:
    # ── Sidebar / Barra Lateral de Filtros ──────────────────────────────────────
    st.sidebar.markdown("## 🚚 Filtros e Parâmetros")
    
    # Lista de municípios ordenados alfabeticamente para o selectbox
    municipios_disponiveis = sorted(list(df_manut_os['nm_municipio'].dropna().unique()))
    opcao_municipio = st.sidebar.selectbox(
        "Selecione o Município:",
        ["Todos os Municípios"] + municipios_disponiveis
    )

    # Barra lateral informativa
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Recorte Temporal:** {ANO}")
    st.sidebar.markdown("**Módulos ETL:** Ativos e Integrados")
    st.sidebar.markdown("**Desenvolvido para:** Centro Universitário Estácio - 2026")

    # ── Filtragem Reativa das Bases de Dados ──────────────────────────────────
    if opcao_municipio == "Todos os Municípios":
        df_manut_filtrado = df_manut_os
        df_veiculos_filtrado = df_veiculos
        df_qr_filtrado = df_qr
        df_invest_filtrado = df_invest
        ne_qr_filtrado = ne_qr
        ne_invest_filtrado = ne_invest
        titulo_dashboard = "Estado do Ceará - Panorama Geral"
    else:
        df_manut_filtrado = df_manut_os[df_manut_os['nm_municipio'] == opcao_municipio]
        # Para os veículos, vamos filtrar os que pertencem ao município correspondente
        # Buscando o código de município
        cd_mun_selecionado = df_manut_filtrado['cd_municipio'].iloc[0] if not df_manut_filtrado.empty else None
        
        if cd_mun_selecionado:
            df_veiculos_filtrado = df_veiculos[df_veiculos['cd_municipio'] == cd_mun_selecionado]
        else:
            df_veiculos_filtrado = df_veiculos[df_veiculos['nm_municipio'] == opcao_municipio]
            
        df_qr_filtrado = df_qr[df_qr['nm_municipio'] == opcao_municipio]
        df_invest_filtrado = df_invest[df_invest['nm_municipio'] == opcao_municipio]
        ne_qr_filtrado = ne_qr[ne_qr['cd_municipio'] == cd_mun_selecionado] if cd_mun_selecionado else ne_qr
        ne_invest_filtrado = ne_invest[ne_invest['cd_municipio'] == cd_mun_selecionado] if cd_mun_selecionado else ne_invest
        titulo_dashboard = f"Município: {opcao_municipio}"

    # ── Título Principal ──────────────────────────────────────────────────────
    st.title("🔎 Auditoria de Manutenção e Frota Municipal")
    st.subheader(titulo_dashboard)
    st.markdown("Dashboard analítico interativo para acompanhamento de gastos públicos e identificação de anomalias contratuais.")

    # ── KPIs principais (Indicadores Rápidos) ─────────────────────────────────
    gasto_total = df_manut_filtrado['vl_total_servicos_vma'].sum()
    qtd_os = len(df_manut_filtrado)
    ticket_medio = df_manut_filtrado['vl_total_servicos_vma'].mean() if qtd_os > 0 else 0.0
    qtd_veiculos_manut = df_manut_filtrado['cd_renavam_vm'].nunique()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container(border=True):
            st.metric(
                label="Total Gasto (OS Válidas)",
                value=f"R$ {gasto_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            )
            
    with col2:
        with st.container(border=True):
            st.metric(
                label="Qtd. Ordens de Serviço (OS)",
                value=f"{qtd_os:,}".replace(",", "."),
            )
            
    with col3:
        with st.container(border=True):
            st.metric(
                label="Ticket Médio / OS",
                value=f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            )
            
    with col4:
        with st.container(border=True):
            st.metric(
                label="Veículos em Manutenção",
                value=f"{qtd_veiculos_manut:,}".replace(",", "."),
            )

    # Spacer
    st.markdown("---")

# ── Seção Central: Ranking de Prestadores e Alertas Textuais (Empilhados) ──
    
    # 1. Gráfico de Prestadores (Ocupando a largura total)
    st.markdown("### 🏆 Top 10 Prestadores de Serviço")
    if not df_manut_filtrado.empty:
        df_prest = (
            df_manut_filtrado.groupby('nm_razao_prest_norm')
            .agg(total_recebido=('vl_total_servicos_vma', 'sum'), qtd_os=('nu_ordem_servico_vma', 'count'))
            .reset_index()
            .sort_values(by='total_recebido', ascending=False)
            .head(10)
        )
        
        fig_prest = px.bar(
            df_prest,
            x='total_recebido',
            y='nm_razao_prest_norm',
            orientation='h',
            labels={'total_recebido': 'Total Recebido (R$)', 'nm_razao_prest_norm': 'Razão Social do Prestador'},
            color='total_recebido',
            color_continuous_scale='OrRd',
            hover_data={'qtd_os': True}
        )
        fig_prest.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            xaxis_tickformat="R$,.2f",
            height=450,
            margin=dict(l=20, r=20, t=10, b=10)
        )
        st.plotly_chart(fig_prest, use_container_width=True)
    else:
        st.info("Nenhum dado de manutenção disponível para este município.")

    # Pequeno espaçador visual para separar o gráfico dos textos
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Caixa de Alertas de Transparência (Logo abaixo do gráfico)
    st.markdown("### ⚠️ Diagnóstico e Alertas de Transparência")
    
    total_gastos_alertas = df_manut_filtrado['vl_total_servicos_vma'].sum()
    
    df_alert_curto = df_manut_filtrado[df_manut_filtrado['alerta_desc_curta'] == True]
    df_alert_agrup = df_manut_filtrado[df_manut_filtrado['alerta_agrupamento'] == True]
    
    gasto_curto = df_alert_curto['vl_total_servicos_vma'].sum()
    gasto_agrup = df_alert_agrup['vl_total_servicos_vma'].sum()
    
    # Dica extra: Embrulhar os alertas em um container com borda deixa o visual limpo e organizado
    with st.container(border=True):
        st.markdown("**1. Falta de Detalhamento Técnico (Descrição Curta < 25 carac.):**")
        st.write(f"- **OSs Afetadas:** {len(df_alert_curto)} ({len(df_alert_curto)/qtd_os*100:.1f}% das OSs)" if qtd_os > 0 else "- **OSs Afetadas:** 0")
        st.write(f"- **Volume Financeiro sob Suspeição:** R$ {gasto_curto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        st.markdown("---")
        st.markdown("**2. OSs Agrupadas (Múltiplos Veículos na Mesma Descrição):**")
        st.write(f"- **OSs Afetadas:** {len(df_alert_agrup)} ({len(df_alert_agrup)/qtd_os*100:.1f}% das OSs)" if qtd_os > 0 else "- **OSs Afetadas:** 0")
        st.write(f"- **Volume Financeiro sob Suspeição:** R$ {gasto_agrup:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    # Spacer
    st.markdown("---")

    # ── Seção Inferior: Quarentena e Estudo Orçamentário ──────────────────────
    col_bottom_left, col_bottom_right = st.columns([1, 1])

    with col_bottom_left:
        st.markdown("### 📥 Triagem e Retenção Financeira")
        
        total_quarentena = df_qr_filtrado['vl_total_servicos_vma'].sum()
        total_investigar = df_invest_filtrado['vl_total_servicos_vma'].sum()
        
        st.write("A triagem analisa o descompasso entre o empenhado e o total executado nas OSs:")
        st.write(f"- **Retido em Quarentena Crítica (Dif. > R$ 100k):** R$ {total_quarentena:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"- **Retido em Investigação Moderada (Dif. > R$ 10k):** R$ {total_investigar:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        # Rosca do descompasso
        if total_quarentena > 0 or total_investigar > 0:
            labels_q = ['Quarentena Crítica', 'Investigação Moderada']
            values_q = [total_quarentena, total_investigar]
            
            fig_pie_q = px.pie(
                names=labels_q,
                values=values_q,
                color=labels_q,
                color_discrete_map={
                    'Quarentena Crítica': '#d9534f',
                    'Investigação Moderada': '#f0ad4e'
                },
                hole=0.4
            )
            fig_pie_q.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_pie_q, use_container_width=True)
        else:
            st.success("Excelente! Nenhuma OS deste município está retida na triagem orçamentária.")

    with col_bottom_right:
        st.markdown("### 🗺️ Dados de Geolocalização (Mapeamento IBGE)")
        st.write("Visualização do De-Para oficial com o IBGE obtido da API do TCE-CE:")
        
        # Filtra os dados de de-para para o município selecionado
        if opcao_municipio == "Todos os Municípios":
            df_ibge_display = df_ibge
        else:
            df_ibge_display = df_ibge[df_ibge['nome_municipio'] == opcao_municipio]
            
        if not df_ibge_display.empty:
            st.dataframe(df_ibge_display.head(10), use_container_width=True, hide_index=True)
        else:
            st.warning("Código IBGE do município não encontrado na API do TCE-CE.")

    # ── Rodapé Informativo ────────────────────────────────────────────────────
    st.markdown("---")
    st.caption("🔍 Auditoria de Manutenção - Frota Municipal 2025. Dados processados pelo pipeline ETL integrado.")
