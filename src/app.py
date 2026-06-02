# src/app.py

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import IsolationForest

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
def carregar_geojson_ceara():
    """Carrega o GeoJSON da malha municipal do Ceará a partir da URL raw do tbrugz."""
    import requests
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-23-mun.json"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        geojson = response.json()
        # Normaliza o id na propriedade e no nível raiz da feature para 6 dígitos
        for feature in geojson.get("features", []):
            if "properties" in feature and "id" in feature["properties"]:
                id_6 = str(feature["properties"]["id"])[:6]
                feature["properties"]["id"] = id_6
                feature["id"] = id_6
        return geojson
    except Exception as e:
        st.error(f"Erro ao carregar o GeoJSON do Ceará: {e}")
        return None

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

    # Adicionar o código IBGE de 6 dígitos ao df_valido (df_manut_os)
    if not df_ibge.empty:
        df_valido = df_valido.merge(
            df_ibge[['cd_municipio', 'codigo_municipio_ibge_6']], 
            on='cd_municipio', 
            how='left'
        )

    # Detecção de Outliers e Score de Suspeição
    if not df_valido.empty:
        X = df_valido[['vl_total_servicos_vma']].dropna()
        if len(X) > 0:
            if_model = IsolationForest(contamination=IF_CONTAMINATION, random_state=42)
            df_valido['outlier_iforest'] = if_model.fit_predict(X)
            df_valido['is_outlier_iforest'] = df_valido['outlier_iforest'] == -1
            
            q1 = df_valido['vl_total_servicos_vma'].quantile(0.25)
            q3 = df_valido['vl_total_servicos_vma'].quantile(0.75)
            iqr = q3 - q1
            limite_superior_iqr = q3 + (LIMIAR_IQR_MULTIPLIER * iqr)
            df_valido['is_outlier_iqr'] = df_valido['vl_total_servicos_vma'] > limite_superior_iqr
            
            mean_p = df_valido['vl_total_servicos_vma'].mean()
            std_p = df_valido['vl_total_servicos_vma'].std()
            if std_p > 0:
                df_valido['z_score'] = (df_valido['vl_total_servicos_vma'] - mean_p) / std_p
            else:
                df_valido['z_score'] = 0.0
            df_valido['is_outlier_zscore'] = df_valido['z_score'].abs() > LIMIAR_ZSCORE
            
            df_valido['score_suspeicao'] = (
                df_valido['is_outlier_iforest'].astype(int) + 
                df_valido['is_outlier_iqr'].astype(int) + 
                df_valido['is_outlier_zscore'].astype(int)
            )
        else:
            df_valido['is_outlier_iforest'] = False
            df_valido['is_outlier_iqr'] = False
            df_valido['is_outlier_zscore'] = False
            df_valido['score_suspeicao'] = 0

    return df_vei, df_valido, df_invest, df_qr, ne_qr, ne_invest, df_loc, df_ibge

# Carregando as bases de dados e o GeoJSON
try:
    df_veiculos, df_manut_os, df_invest, df_qr, ne_qr, ne_invest, df_locados, df_ibge = load_all_data()
    geojson_data = carregar_geojson_ceara()
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

    # ── Mapa de Calor do Ceará (Geolocalização) ──────────────────────────────
    if geojson_data is not None and not df_manut_filtrado.empty:
        # Agrupar dados por codigo_municipio_ibge_6 para o mapa
        df_mapa = (
            df_manut_filtrado.groupby('codigo_municipio_ibge_6')
            .agg(
                total_gasto=('vl_total_servicos_vma', 'sum'),
                nm_municipio=('nm_municipio', 'first')
            )
            .reset_index()
        )
        
        # Gerar mapa cloroplético interativo
        fig_mapa = px.choropleth(
            df_mapa,
            geojson=geojson_data,
            locations="codigo_municipio_ibge_6",
            color="total_gasto",
            color_continuous_scale="Reds",
            labels={"total_gasto": "Total Gasto (R$)", "codigo_municipio_ibge_6": "Código IBGE"},
            hover_name="nm_municipio",
            hover_data={"total_gasto": ":,.2f"}
        )
        
        fig_mapa.update_geos(
            fitbounds="locations",
            visible=False
        )
        
        fig_mapa.update_layout(
            margin=dict(l=0, r=0, t=10, b=10),
            height=450
        )
        
        st.plotly_chart(fig_mapa, use_container_width=True)
    elif geojson_data is None:
        st.warning("Não foi possível carregar o mapa: GeoJSON do Ceará indisponível.")

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

    # ── Estrutura de Abas ─────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        'Perfil da Frota', 
        'Análise de Gastos e Prestadores', 
        'Modelos Antifraude & Quarentena'
    ])

    # ── TAB 1: Perfil da Frota ────────────────────────────────────────────────
    with tab1:
        st.markdown("### 📊 Perfil e Distribuição da Frota")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.markdown("#### Situação Real da Frota")
            if not df_veiculos_filtrado.empty:
                df_situacao = df_veiculos_filtrado['situacao_real'].value_counts().reset_index()
                df_situacao.columns = ['Situação Real', 'Quantidade']
                
                fig_situacao = px.bar(
                    df_situacao,
                    x='Situação Real',
                    y='Quantidade',
                    title=f'Situação Real da Frota - {opcao_municipio}',
                    color='Situação Real',
                    color_continuous_scale='Viridis',
                    text_auto=True
                )
                fig_situacao.update_layout(showlegend=False, template='plotly_white')
                st.plotly_chart(fig_situacao, use_container_width=True)
            else:
                st.info("Nenhum veículo cadastrado disponível para este município.")
                
        with col_f2:
            st.markdown("#### Distribuição de Idade dos Veículos por Tipo de Vínculo")
            if not df_veiculos_filtrado.empty:
                df_veiculos_filtrado_copy = df_veiculos_filtrado.copy()
                df_veiculos_filtrado_copy['vínculo_descr'] = df_veiculos_filtrado_copy['tp_vinculacao_vm'].map(TIPO_VINCULACAO).fillna(df_veiculos_filtrado_copy['tp_vinculacao_vm'])
                
                fig_idade = px.box(
                    df_veiculos_filtrado_copy,
                    x='vínculo_descr',
                    y='idade_veiculo',
                    color='vínculo_descr',
                    title=f'Distribuição de Idade por Tipo de Vínculo - {opcao_municipio}',
                    labels={'vínculo_descr': 'Tipo de Vínculo', 'idade_veiculo': 'Idade (Anos)'}
                )
                fig_idade.update_layout(showlegend=False, template='plotly_white')
                st.plotly_chart(fig_idade, use_container_width=True)
            else:
                st.info("Nenhum veículo cadastrado disponível para este município.")

    # ── TAB 2: Análise de Gastos e Prestadores ────────────────────────────────
    with tab2:
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
                title=f'Top 10 Prestadores de Serviço - {opcao_municipio}',
                color='total_recebido',
                color_continuous_scale='OrRd',
                hover_data={'qtd_os': True}
            )
            fig_prest.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                xaxis_tickformat="R$,.2f",
                height=400,
                margin=dict(l=20, r=20, t=30, b=10)
            )
            st.plotly_chart(fig_prest, use_container_width=True)
        else:
            st.info("Nenhum dado de manutenção disponível para este município.")
            
        st.markdown("### 📊 Top 20 Municípios por Volume de Gastos")
        if not df_manut_filtrado.empty:
            gastos_por_municipio = (
                df_manut_filtrado.groupby(['cd_municipio', 'nm_municipio'])
                .agg(
                    total_gasto=('vl_total_servicos_vma', 'sum'),
                    qtd_manutencoes=('nu_ordem_servico_vma', 'count'),
                    ticket_medio=('vl_total_servicos_vma', 'mean')
                )
                .reset_index()
                .sort_values(by='total_gasto', ascending=False)
            )
            
            fig_gastos_mun = px.bar(
                gastos_por_municipio.head(20), 
                x='nm_municipio', 
                y='total_gasto',
                title=f'Top 20 Municípios do Ceará por Gastos - {opcao_municipio}',
                labels={'nm_municipio': 'Município', 'total_gasto': 'Total Gasto (R$)'},
                color='total_gasto',
                color_continuous_scale='Viridis',
                hover_data={'qtd_manutencoes': True, 'ticket_medio': ':,.2f'}
            )
            fig_gastos_mun.update_layout(
                xaxis_tickangle=-45, 
                template='plotly_white',
                yaxis_tickformat="R$,.2f",
                height=400
            )
            st.plotly_chart(fig_gastos_mun, use_container_width=True)
        else:
            st.info("Nenhum dado de manutenção disponível para este município.")
            
        col_t2_l, col_t2_r = st.columns(2)
        
        with col_t2_l:
            st.markdown("### ⚠️ Diagnóstico e Alertas de Transparência")
            if not df_manut_filtrado.empty:
                df_alert_curto = df_manut_filtrado[df_manut_filtrado['alerta_desc_curta'] == True]
                df_alert_agrup = df_manut_filtrado[df_manut_filtrado['alerta_agrupamento'] == True]
                
                gasto_curto = df_alert_curto['vl_total_servicos_vma'].sum()
                gasto_agrup = df_alert_agrup['vl_total_servicos_vma'].sum()
                
                with st.container(border=True):
                    st.markdown("**1. Falta de Detalhamento Técnico (Descrição Curta < 25 carac.):**")
                    st.write(f"- **OSs Afetadas:** {len(df_alert_curto)} ({len(df_alert_curto)/qtd_os*100:.1f}% das OSs)" if qtd_os > 0 else "- **OSs Afetadas:** 0")
                    st.write(f"- **Volume Financeiro sob Suspeição:** R$ {gasto_curto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    
                    st.markdown("---")
                    st.markdown("**2. OSs Agrupadas (Múltiplos Veículos na Mesma Descrição):**")
                    st.write(f"- **OSs Afetadas:** {len(df_alert_agrup)} ({len(df_alert_agrup)/qtd_os*100:.1f}% das OSs)" if qtd_os > 0 else "- **OSs Afetadas:** 0")
                    st.write(f"- **Volume Financeiro sob Suspeição:** R$ {gasto_agrup:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            else:
                st.info("Sem dados para análise de transparência.")
                
        with col_t2_r:
            st.markdown("### 🗺️ Dados de Geolocalização (Mapeamento IBGE)")
            st.write("Visualização do De-Para oficial com o IBGE obtido da API do TCE-CE:")
            
            if opcao_municipio == "Todos os Municípios":
                df_ibge_display = df_ibge
            else:
                df_ibge_display = df_ibge[df_ibge['nome_municipio'] == opcao_municipio]
                
            if not df_ibge_display.empty:
                st.dataframe(df_ibge_display.head(10), use_container_width=True, hide_index=True)
            else:
                st.warning("Código IBGE do município não encontrado na API do TCE-CE.")

    # ── TAB 3: Modelos Antifraude & Quarentena ────────────────────────────────
    with tab3:
        st.markdown("### 🔎 Detecção de Outliers Críticos (Isolation Forest + IQR + Z-Score)")
        if not df_manut_filtrado.empty and 'score_suspeicao' in df_manut_filtrado.columns:
            df_plot_outliers = df_manut_filtrado.sort_values(by='vl_total_servicos_vma', ascending=False).head(500)
            
            fig_outliers = px.scatter(
                df_plot_outliers,
                x='dt_ordem_servico_vma',
                y='vl_total_servicos_vma',
                color='score_suspeicao',
                size='vl_total_servicos_vma',
                color_continuous_scale='Reds',
                title=f'Top {len(df_plot_outliers)} Ordens de Serviço mais Suspeitas - {opcao_municipio}',
                labels={'dt_ordem_servico_vma': 'Data da OS', 'vl_total_servicos_vma': 'Valor da OS (R$)', 'score_suspeicao': 'Modelos que Retiveram'},
                hover_data=['nm_municipio', 'nm_razao_prest_norm', 'de_servicos_vma']
            )
            fig_outliers.update_layout(template='plotly_white', yaxis_tickformat="R$,.2f")
            st.plotly_chart(fig_outliers, use_container_width=True)
            
            # Volumetria na interface
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Outliers Isolation Forest", f"{df_manut_filtrado['is_outlier_iforest'].sum()} OS")
            with c2:
                st.metric("Outliers IQR (Limiar 1.5)", f"{df_manut_filtrado['is_outlier_iqr'].sum()} OS")
            with c3:
                st.metric("Outliers Z-Score (Limiar 3.0)", f"{df_manut_filtrado['is_outlier_zscore'].sum()} OS")
        else:
            st.info("Nenhum dado de manutenção ou score de suspeição disponível para este município.")
            
        st.markdown("### 📥 Triagem e Retenção Financeira")
        col_t3_l, col_t3_r = st.columns([1.2, 1])
        
        with col_t3_l:
            total_quarentena = ne_qr_filtrado['dif'].sum() if not ne_qr_filtrado.empty else 0.0
            total_investigar = ne_invest_filtrado['dif'].sum() if not ne_invest_filtrado.empty else 0.0
            
            st.write("A triagem analisa o descompasso entre o empenhado e o total executado nas OSs:")
            st.write(f"- **Retido em Quarentena Crítica (Dif. > R$ 100k):** R$ {total_quarentena:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.write(f"- **Retido em Investigação Moderada (Dif. > R$ 10k):** R$ {total_investigar:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            if total_quarentena > 0 or total_investigar > 0:
                resumo_auditoria = pd.DataFrame({
                    'Categoria': ['Divergência Crítica (Quarentena)', 'Divergência Moderada (Investigar)'],
                    'Qtd Notas Empenho': [len(ne_qr_filtrado), len(ne_invest_filtrado)],
                    'Total Divergência (R$)': [total_quarentena, total_investigar]
                })
                
                fig_quarentena = px.pie(
                    resumo_auditoria, 
                    values='Total Divergência (R$)', 
                    names='Categoria',
                    title=f'Divergências Orçamentárias Triadas - {opcao_municipio}',
                    color='Categoria',
                    color_discrete_map={
                        'Divergência Crítica (Quarentena)': '#d9534f',
                        'Divergência Moderada (Investigar)': '#f0ad4e'
                    },
                    hole=0.4
                )
                fig_quarentena.update_traces(textinfo='percent+label', textfont_size=14)
                fig_quarentena.update_layout(template='plotly_white', height=280, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_quarentena, use_container_width=True)
            else:
                st.success("Excelente! Nenhuma OS deste município está retida na triagem orçamentária.")
                
        with col_t3_r:
            st.write("**Notas de Empenho sob Alerta Financeiro:**")
            if not ne_qr_filtrado.empty or not ne_invest_filtrado.empty:
                ne_alertas = pd.concat([ne_qr_filtrado, ne_invest_filtrado]).sort_values(by='dif', ascending=False)
                st.dataframe(
                    ne_alertas[['nu_nota_empenho', 'status_ne', 'soma_os', 'vl_empenhado_ne', 'dif']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma nota de empenho sob suspeição nesta área.")

    # ── Rodapé Informativo ────────────────────────────────────────────────────
    st.markdown("---")
    st.caption("🔍 Auditoria de Manutenção - Frota Municipal 2025. Dados processados pelo pipeline ETL integrado.")
