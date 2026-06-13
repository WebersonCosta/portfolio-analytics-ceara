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

    print("\n=== VERIFICANDO RATEIO APÓS CORREÇÃO ===")
    df_check = df_locados[df_locados['nu_contrato_pai'] == '0954']
    print(df_check[['cd_renavam_vm','nu_contrato_pai','dt_ref_vl','custo_locacao_anual']].to_string())
    print("\nTipo de nu_contrato_pai:", df_locados['nu_contrato_pai'].dtype)
    print("Tipo de dt_ref_vl:", df_locados['dt_ref_vl'].dtype)


    print("=== VERIFICAÇÃO PÓS-CORREÇÃO ===")
    print("Distribuição de custo_locacao_anual (df_veiculos, só > 0):")
    print(df_veiculos[df_veiculos['custo_locacao_anual']>0]['custo_locacao_anual'].describe())
    print("\nSoma total custo_locacao_anual em df_veiculos:", df_veiculos['custo_locacao_anual'].sum())

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
    if geojson_data is not None and not df_manut_filtrado.empty and 'codigo_municipio_ibge_6' in df_manut_filtrado.columns:
        df_mapa = (
            df_manut_filtrado.groupby('codigo_municipio_ibge_6')
            .agg(
                total_gasto=('vl_total_servicos_vma', 'sum'),
                nm_municipio=('nm_municipio', 'first')
            )
            .reset_index()
        )
        
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
        
        todos_ids = [f["id"] for f in geojson_data.get("features", [])]
        camada_fundo = go.Choropleth(
            geojson=geojson_data,
            locations=todos_ids,
            z=[0] * len(todos_ids),
            colorscale=[[0, 'rgba(245, 245, 245, 0.4)'], [1, 'rgba(245, 245, 245, 0.4)']],
            showscale=False,
            marker=dict(line=dict(color="rgba(160, 160, 160, 0.5)", width=0.7)),
            hoverinfo='skip'
        )
        
        fig_mapa.add_trace(camada_fundo)
        fig_mapa.data = (fig_mapa.data[-1],) + fig_mapa.data[:-1]
        
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
    else:
        st.warning("⚠️ O mapa de calor está indisponível porque os dados do IBGE não puderam ser carregados via API do TCE-CE.")

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
            # O argumento 'help' adiciona o ícone de informação reativo com o hover do mouse
            st.markdown(
                "#### Distribuição de Idade dos Veículos por Tipo de Vínculo",
help="""
💡 **Como ler este gráfico (Boxplot):**

O Boxplot mostra a dispersão e a idade da frota do município:
* **Linha Central da Caixa:** É a Mediana. Metade da frota está acima dessa 
idade, metade está abaixo.
* **A Caixa Colorida:** Concentra os 50% dos veículos mais comuns da frota.
* **Linhas Horizontais Extremas (Bigodes):** Representam a idade mínima e 
máxima da frota dentro do padrão normal.
* **Pontos Isolados (Outliers):** Veículos que estão fora da curva 
(ex: um carro de 20 anos em uma frota que tem média de 4 anos). 
Indica frotas possivelmente defasadas.
"""
)
            
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

        # ── 🔎 INVESIGAÇÃO DETALHADA (Aparece apenas se um município for selecionado) ──
        if opcao_municipio != "Todos os Municípios":
            st.markdown("---")
            st.markdown(f"### 🔎 Investigação Detalhada da Frota: {opcao_municipio}")
            st.markdown("Métricas focadas na identificação de veículos e prestadores locais com maior acúmulo de despesas.")

            if not df_manut_filtrado.empty:
                # Criamos uma cópia segura dos dados já filtrados do município
                manut_mun = df_manut_filtrado.copy()
                
                # Garante que temos placa, marca e modelo fazendo o merge com o cadastro de veículos
                colunas_veiculos = ['cd_renavam_vm', 'cd_placa_vm', 'de_marca_vm', 'de_modelo_versao_vm']
                colunas_existentes_vei = [c for c in colunas_veiculos if c in df_veiculos.columns]
                
                # Remove duplicadas do cadastro de veículos pelo renavam antes de cruzar
                df_vei_lookup = df_veiculos[colunas_existentes_vei].drop_duplicates('cd_renavam_vm')
                
                # Remove colunas duplicadas da base de manutenção se já existirem antes do merge
                colunas_para_dropar = [c for c in ['cd_placa_vm', 'de_marca_vm', 'de_modelo_versao_vm'] if c in manut_mun.columns]
                if colunas_para_dropar:
                    manut_mun = manut_mun.drop(columns=colunas_para_dropar)
                
                manut_mun = manut_mun.merge(df_vei_lookup, on='cd_renavam_vm', how='left')

                # Cria duas colunas paralelas no Streamlit para colocar as análises lado a lado
                col_inv1, col_inv2 = st.columns(2)

                with col_inv1:
                    st.markdown("#### 🚗 Veículos 'Campeões' de Gasto (Top 5)")
                    
                    # Agrupa trazendo Placa, Marca e Modelo para o resultado final
                    top_gastadores = (
                        manut_mun.groupby(['cd_placa_vm', 'de_marca_vm', 'de_modelo_versao_vm'])['vl_total_servicos_vma']
                        .agg(total_gasto='sum', qtd_ordens='count')
                        .sort_values('total_gasto', ascending=False)
                        .head(5)
                        .reset_index()
                    )

                    if not top_gastadores.empty:
                        st.dataframe(
                            top_gastadores,
                            column_config={
                                "cd_placa_vm": "Placa",
                                "de_marca_vm": "Marca",
                                "de_modelo_versao_vm": "Modelo",
                                "total_gasto": st.column_config.NumberColumn("Total Gasto", format="R$ %,.2f"),
                                "qtd_ordens": st.column_config.NumberColumn("Qtd OS", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("Sem dados suficientes para mapear os veículos.")

                with col_inv2:
                    st.markdown("#### 🛠️ Prestadores que mais faturaram no município (Top 5)")
                    
                    top_prestadores = (
                        manut_mun.groupby('nm_razao_prest_norm')['vl_total_servicos_vma']
                        .agg(total_faturado='sum', qtd_ordens='count')
                        .sort_values('total_faturado', ascending=False)
                        .head(5)
                        .reset_index()
                    )

                    if not top_prestadores.empty:
                        st.dataframe(
                            top_prestadores,
                            column_config={
                                "nm_razao_prest_norm": "Razão Social do Prestador",
                                "total_faturado": st.column_config.NumberColumn("Total Faturado", format="R$ %,.2f"),
                                "qtd_ordens": st.column_config.NumberColumn("Qtd OS", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("Sem dados suficientes para mapear os prestadores.")
            else:
                st.info("Nenhum dado de manutenção registrado para este município.")

        # ── 🔎 INVESTIGAÇÃO DETALHADA (Adicionando a análise orçamentária do Professor) ──
        if opcao_municipio != "Todos os Municípios":
            st.markdown("---")
            st.markdown(f"### 📊 Impacto Orçamentário por Secretaria: {opcao_municipio} (2025)")
            st.write("Esta análise cruza o gasto real de manutenção com o orçamento total fixado para cada órgão na LOA via API do TCE-CE.")

            # 1. Descobrir o código do município atual para consultar a API
            # Presumindo que df_manut_filtrado tem a coluna 'cd_municipio'
            if not df_manut_filtrado.empty:
                cd_mun_api = str(df_manut_filtrado['cd_municipio'].iloc[0]).zfill(3)
                
                # Consome a API do TCE-CE em tempo de execução usando um cache para não estressar a API
                @st.cache_data(ttl=3600)
                def carregar_orcamento_tce(codigo_municipio):
                    import requests
                    url = f"https://api-dados-abertos.tce.ce.gov.br/sim/orcamento_despesa?codigo_municipio={codigo_municipio}&exercicio_orcamento=202500"
                    try:
                        response = requests.get(url, timeout=10)
                        if response.status_code == 200:
                            dados = response.json()
                            if "elements" in dados and dados["elements"]:
                                return pd.DataFrame(dados["elements"])
                    except Exception as e:
                        pass
                    return pd.DataFrame()

                df_orc_api = carregar_orcamento_tce(cd_mun_api)

                if not df_orc_api.empty:
                    # 2. Processa o Orçamento Total Fixado por Órgão (Secretaria)
                    # Força o código do órgão a ser string e limpa espaços para o merge bater correto
                    df_orc_api['codigo_orgao'] = df_orc_api['codigo_orgao'].astype(str).str.strip().str.zfill(2)
                    
                    # Agrupa o orçamento total fixado da secretaria (soma todos os elementos de despesa dela)
                    df_orc_agrupado = (
                        df_orc_api.groupby('codigo_orgao')['valor_total_fixado']
                        .sum()
                        .reset_index()
                        .rename(columns={'valor_total_fixado': 'Orcamento_Total_Fixado'})
                    )

                    # 3. Processa o Gasto de Manutenção Atual do Município por Órgão
                    manut_mun = df_manut_filtrado.copy()
                    manut_mun['cd_orgao'] = manut_mun['cd_orgao'].astype(str).str.strip().str.zfill(2)
                    
                    df_manut_orgao = (
                        manut_mun.groupby(['cd_orgao', 'nm_orgao'])['vl_total_servicos_vma']
                        .sum()
                        .reset_index()
                        .rename(columns={'vl_total_servicos_vma': 'Gasto_Manutencao'})
                    )

                    # 4. Realiza o Cruzamento (Merge) das Duas Realidades
                    df_impacto = pd.merge(
                        df_manut_orgao,
                        df_orc_agrupado,
                        left_on='cd_orgao',
                        right_on='codigo_orgao',
                        how='inner'
                    )

                    # 5. Calcula a Métrica solicitada pelo seu professor
                    df_impacto['%_Gasto_Manutencao'] = (df_impacto['Gasto_Manutencao'] / df_impacto['Orcamento_Total_Fixado']) * 100
                    
                    # Ordena pelas secretarias onde a manutenção engoliu a maior fatia do orçamento
                    df_impacto = df_impacto.sort_values(by='%_Gasto_Manutencao', ascending=False)

                    # 6. Renderiza na Interface do Streamlit
                    st.dataframe(
                        df_impacto,
                        column_config={
                            "cd_orgao": "Cód.",
                            "nm_orgao": "Secretaria / Órgão",
                            "Gasto_Manutencao": st.column_config.NumberColumn("Gasto Manutenção", format="R$ %,.2f"),
                            "Orcamento_Total_Fixado": st.column_config.NumberColumn("Orçamento Total Fixado", format="R$ %,.2f"),
                            "%_Gasto_Manutencao": st.column_config.NumberColumn("% do Orçamento Consumido", format="%.2f %%"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.warning("⚠️ Não foi possível extrair os dados de orçamento deste município na API do TCE-CE para o exercício de 2025.")
            else:
                st.info("Sem dados de manutenção para mapear o orçamento municipal.")

    # ── TAB 2: Análise de Gastos e Viabilidade de Frota ───────────────────────
    with tab2:
        # Cálculo global e seguro do total de OS para evitar NameError nas métricas abaixo
        total_os_filtrado = len(df_manut_filtrado) if not df_manut_filtrado.empty else 0

        st.markdown("### ⚖️ Viabilidade Financeira: TCO (Custo Total de Propriedade) por Tipo de Vínculo")
        st.write(
            "Esta análise fornece subsídios estratégicos para a tomada de decisão de gastos públicos, "
            "comparando o Custo Total Anual por veículo entre frotas Próprias e Locadas. "
            "Para a frota locada, o custo considera o **valor do contrato de locação anualizado** "
            "somado aos gastos de manutenção pagos diretamente pelo município."
        )

        if not df_manut_filtrado.empty and not df_veiculos_filtrado.empty:
            # Base de frota em operação
            df_frota_ativos = df_veiculos_filtrado[df_veiculos_filtrado['situacao_real'] == 'Em Operação']
            
            # --- PROCESSAMENTO: FROTA PRÓPRIA ---
            # (TCO da frota própria = só manutenção, pois não há custo de "aluguel")
            qtd_p = df_frota_ativos[df_frota_ativos['tp_vinculacao_vm'] == 'p']['cd_renavam_vm'].nunique()
            total_p = df_manut_filtrado[df_manut_filtrado['tp_vinculacao_vm'] == 'p']['vl_total_servicos_vma'].sum()
            custo_p = total_p / qtd_p if qtd_p > 0 else 0.0
            
            # --- PROCESSAMENTO: FROTA LOCADA — TCO (Locação Anualizada + Manutenção Residual) ---
            # 🆕 Agora consideramos TODOS os veículos locados ativos (não só os sem cobertura),
            # pois o custo de locação entra para todos.
            df_locados_ativos = df_frota_ativos[df_frota_ativos['tp_vinculacao_vm'] == 'l']

            # Separa os que têm custo de locação anualizável de forma confiável
            df_locados_tco_ok = df_locados_ativos[df_locados_ativos['custo_loc_anualizavel'] == True]
            df_locados_sem_tco = df_locados_ativos[df_locados_ativos['custo_loc_anualizavel'] == False]

            qtd_l = df_locados_tco_ok['cd_renavam_vm'].nunique()
            qtd_l_excluidos = df_locados_sem_tco['cd_renavam_vm'].nunique()

            total_locacao = (
                df_locados_tco_ok
                .drop_duplicates(subset='cd_renavam_vm')['custo_locacao_anual']
                .sum()
            )

            total_manut_l = df_manut_filtrado[
                (df_manut_filtrado['tp_vinculacao_vm'] == 'l') & 
                (df_manut_filtrado['loc_manut_inclusa'] == False) &
                (df_manut_filtrado['cd_renavam_vm'].isin(df_locados_tco_ok['cd_renavam_vm']))
            ]['vl_total_servicos_vma'].sum()

            custo_l = (total_locacao + total_manut_l) / qtd_l if qtd_l > 0 else 0.0

            # Aviso sobre exclusões
            if qtd_l_excluidos > 0:
                st.caption(
                    f"⚠️ {qtd_l_excluidos} veículos locados com remuneração por **Quilometragem/Hora/Quinzena** "
                    f"foram excluídos deste TCO por falta de dados de quantidade contratada para anualização."
                )
            
            # ── 📐 RENDERIZAÇÃO DOS BLOCOS VISUAIS COMPARATIVOS (MÉTRICAS) ──
            c_prop, c_loc = st.columns(2)
            
            with c_prop:
                st.info("🏢 MODELO: FROTA PRÓPRIA")
                if qtd_p > 0:
                    st.metric("Custo Total Anual / Veículo (TCO)", f"R$ {custo_p:,.2f}")
                    st.caption(f"**Frota Ativa:** {qtd_p} veículos | **Gasto Oficinas:** R$ {total_p:,.2f}")
                else:
                    st.metric("Custo Total Anual / Veículo (TCO)", "R$ 0,00")
                    st.caption("Nenhum veículo próprio ativo identificado nesta seleção.")
                    
            with c_loc:
                st.warning("🚗 MODELO: FROTA LOCADA")
                if qtd_l > 0:
                    st.metric("Custo Total Anual / Veículo (TCO)", f"R$ {custo_l:,.2f}")
                    # 🆕 Caption agora detalha a composição do TCO
                    st.caption(
                        f"**Frota Ativa:** {qtd_l} veículos | "
                        f"**Locação:** R\\$ {total_locacao:,.2f} | "
                        f"**Manutenção (sem cobertura):* * R\\$ {total_manut_l:,.2f}"
                    )
                else:
                    st.metric("Custo Total Anual / Veículo (TCO)", "R$ 0,00")
                    st.caption("Nenhum veículo locado ativo identificado nesta seleção.")

            # ── 💡 INSIGHT LOGÍSTICO PARA O GESTOR MUNICIPAL ──────────────────
            dif_custo = custo_p - custo_l
            
            st.markdown("#### 🧠 Indicador de Suporte à Decisão")
            if dif_custo > 0:
                st.write(
                    f"No cenário selecionado, manter um veículo de **Frota Própria** custa em média "
                    f"**R$ {dif_custo:,.2f} a mais por ano (TCO)** do que um veículo **Locado** "
                    f"(considerando o valor do contrato de locação anualizado somado à manutenção residual). "
                    f"Esse indicador sugere que, mesmo somando o custo do contrato de aluguel, "
                    f"o modelo locado tende a ser mais eficiente que manter a frota própria."
                )
            else:
                st.write(
                    f"No cenário selecionado, o modelo de **Frota Locada** gerou um Custo Total Anual (TCO) de "
                    f"**R$ {abs(dif_custo):,.2f} a mais** por veículo em relação à frota própria. "
                    f"Este dado indica que, para este recorte, o valor do contrato de locação somado à manutenção residual "
                    f"supera o custo de manter a frota própria."
                )

            # ── 📊 GRÁFICO COMPARATIVO DE CUSTO UNITÁRIO (TCO) ──
            df_custo_comp = pd.DataFrame({
                "Modelo de Frota": ["Frota Própria", "Frota Locada (TCO)"],
                "Custo Total Anual (R$)": [custo_p, custo_l],
                "Cor_Apresentacao": ["#1f77b4", "#ff7f0e"] # Azul para própria, Laranja para locada
            })

            fig_comp_custo = px.bar(
                df_custo_comp,
                x="Custo Total Anual (R$)",
                y="Modelo de Frota",
                orientation="h",
                color="Modelo de Frota",
                color_discrete_map={
                    "Frota Própria": "#2196F3", 
                    "Frota Locada (TCO)": "#FF9800"
                },
                title="Comparativo: Custo Total Anual (TCO) por Veículo Único"
            )

            fig_comp_custo.update_layout(
                template="plotly_white",
                xaxis_tickformat="R$,.2f",
                height=250,
                showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Custo Total Anual por Veículo (TCO)",
                yaxis_title=""
            )

            fig_comp_custo.update_traces(
                texttemplate="R$ %{x:,.2f}",
                textposition="outside",
                cliponaxis=False
            )

            st.plotly_chart(fig_comp_custo, use_container_width=True)
            
        else:
            st.info("Dados insuficientes para calcular a viabilidade de custos por tipo de vínculo.")
            
        st.markdown("---")
        
        # ── 🏆 TOP 10 PRESTADORES DE SERVIÇO ─────────────────────────────────
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
            
        # ── 📊 TOP 20 MUNICÍPIOS POR VOLUME DE GASTOS (Condicional de Contexto) ─
        if opcao_municipio == "Todos os Municípios":
            st.markdown("---")
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
                    title='Top 20 Municípios do Ceará por Volume de Gastos',
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
                st.info("Nenhum dado de manutenção disponível para processar o ranking estadual.")
                
        st.markdown("---")
        
        # ── 🏗️ DIAGNÓSTICO DE TRANSPARÊNCIA E GEOLOCALIZAÇÃO ──────────────────
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
                    # Uso da variável global total_os_filtrado para evitar o NameError
                    st.write(f"- **OSs Afetadas:** {len(df_alert_curto)} ({len(df_alert_curto)/total_os_filtrado*100:.1f}% das OSs)" if total_os_filtrado > 0 else "- **OSs Afetadas:** 0")
                    st.write(f"- **Volume Financeiro sob Suspeição:** R$ {gasto_curto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    
                    st.markdown("---")
                    st.markdown("**2. OSs Agrupadas (Múltiplos Veículos na Mesma Descrição):**")
                    st.write(f"- **OSs Afetadas:** {len(df_alert_agrup)} ({len(df_alert_agrup)/total_os_filtrado*100:.1f}% das OSs)" if total_os_filtrado > 0 else "- **OSs Afetadas:** 0")
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
        st.markdown("### 🔎 Detecção de Outliers Críticos (Isolation Forest + IQR + Z-Score)",
help="""
🤖 **Engenharia de Triagem Antifraude (Como os Modelos Avaliam a Variável**

O sistema avalia individualmente o valor de cada Ordem de Serviço usando três camadas independentes de validação matemática:

1. **Isolation Forest:** O algoritmo de Machine Learning analisa a distribuição do valor total de serviço. Ele tenta isolar cada ponto criando partições aleatórias. Notas com valores muito atípicos são isoladas rapidamente nas primeiras quebras da árvore, recebendo o rótulo `-1`, o que ativa a nossa flag como verdadeira.

2. **Amplitude Interquartil:** Modelo estatístico focado no corpo da distribuição. O código calcula os limites dos dados normais:
* `q1` (25% das OSs mais baratas) e `q3` (75% das OSs mais baratas).
* A diferença cria a amplitude `iqr = q3 - q1`.
* O limite de normalidade é definido pelo limite superior iqr = q3 + (1.5 * iqr)`. Qualquer ordem de serviço cujo valor ultrapasse essa barreira ativa a flag de outlier.

3. **Z-Score Estatístico:** Mede a quantos desvios padrões o valor da OS está afastado da média do município. O cálculo subtrai a média do valor e divide pelo desvio padrão. Se o resultado absoluto for maior que o nosso limiar LIMIAR_ZSCORE = 3.0, significa que a despesa está em uma zona de raridade estatística extrema (ocorre em menos de 1% dos casos).

🎯 **Score de Suspeição (`score_suspeicao`):** O pipeline converte as 3 flags booleanas em inteiros (`0` ou `1`) e realiza o somatório das três camadas. 
* **Score 1 ou 2:** Alerta moderado (a nota falhou em uma ou duas regras).
* **Score 3:** Alerta Máximo Crítico. Significa que a Ordem de Serviço foi considerada uma anomalia grave simultaneamente pelo algoritmo de IA, pelo cálculo de quartis (IQR) e pelo desvio padrão (Z-Score). Essas são as bolhas maiores e mais escuras no topo do gráfico.
""")
        if not df_manut_filtrado.empty and 'score_suspeicao' in df_manut_filtrado.columns:
            df_plot_outliers = df_manut_filtrado.sort_values(by='vl_total_servicos_vma', ascending=False).head(500).copy()
            
            # ── 🔄 FUNÇÃO AUXILIAR PARA QUEBRAR O TEXTO LONGO ──────────────────
            def quebrar_texto(texto, limite=60):
                if pd.isna(texto):
                    return ""
                texto_str = str(texto)
                # Divide o texto em blocos de caracteres sem quebrar palavras ao meio
                import textwrap
                linhas = textwrap.wrap(texto_str, width=limite)
                return "<br>".join(linhas)

            # Aplica a quebra de linha na coluna que vai para o gráfico
            df_plot_outliers['de_servicos_vma_quebrado'] = df_plot_outliers['de_servicos_vma'].apply(quebrar_texto)
            
            fig_outliers = px.scatter(
                df_plot_outliers,
                x='dt_ordem_servico_vma',
                y='vl_total_servicos_vma',
                color='score_suspeicao',
                size='vl_total_servicos_vma',
                color_continuous_scale='Reds',
                title=f'Top {len(df_plot_outliers)} Ordens de Serviço mais Suspeitas - {opcao_municipio}',
                labels={
                    'dt_ordem_servico_vma': 'Data da OS', 
                    'vl_total_servicos_vma': 'Valor da OS (R$)', 
                    'score_suspeicao': 'Modelos que Retiveram',
                    'de_servicos_vma_quebrado': 'Descrição dos Serviços' # Label amigável
                },
                # Trocamos a coluna original pela coluna com as quebras <br>
                hover_data={
                    'nm_municipio': True,
                    'nm_razao_prest_norm': True,
                    'de_servicos_vma_quebrado': True,
                    'vl_total_servicos_vma': ':.2f'
                }
            )
            
            # ── 📐 AJUSTE DA LARGURA E DESIGN DA CAIXA DE HOVER ────────────────
            fig_outliers.update_layout(
                template='plotly_white', 
                yaxis_tickformat="R$,.2f",
                hoverlabel=dict(
                    font_size=12,
                    font_family="Arial",
                    # namelength=-1 garante que o nome da variável não seja cortado
                    namelength=-1 
                )
            )
            
            # Força a largura máxima do bloco de hover para evitar estouros visuais
            fig_outliers.update_traces(
                hoverlabel=dict(
                    align="left"
                )
            )
            
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

        # ── 🚨 ALERTA DE IRREGULARIDADE: MANUTENÇÃO EM VEÍCULO COM CONTRATO COBERTO ──
        st.markdown("---")
        st.markdown("### 💸 Alerta de Conformidade: Duplicidade de Custos em Frota Locada")
        st.write(
            "Este módulo identifica potenciais irregularidades operacionais: Ordens de Serviço pagas pelo município "
            "para veículos locados cujo contrato de locação previa **cobertura integral de manutenção** pela locadora contratada."
        )

        if not df_manut_filtrado.empty:
            # Filtra OSs onde a manutenção estava inclusa no contrato de locação, mas gerou gasto público direto
            df_duplicidade = df_manut_filtrado[
                (df_manut_filtrado['tp_vinculacao_vm'] == 'l') & 
                (df_manut_filtrado['loc_manut_inclusa'] == True)
            ].copy()

            if not df_duplicidade.empty:
                total_desvio_potencial = df_duplicidade['vl_total_servicos_vma'].sum()
                qtd_os_duplicadas = len(df_duplicidade)
                veiculos_afetados = df_duplicidade['cd_renavam_vm'].nunique()

                # Card de Alerta Crítico
                st.error(
                    f"⚠️ **Atenção Auditoria:** Foram identificadas **{qtd_os_duplicadas} Ordens de Serviço** "
                    f"em **{veiculos_afetados} veículos locados** com manutenção inclusa em contrato. "
                    f"O volume financeiro total pago indevidamente soma **R$ {total_desvio_potencial:,.2f}**."
                )

                # Tabela detalhada para o auditor investigar em campo
                st.write("📋 **Relação de Despesas sob Suspeição de Duplicidade:**")
                st.dataframe(
                    df_duplicidade.sort_values(by='vl_total_servicos_vma', ascending=False),
                    column_config={
                        "nu_ordem_servico_vma": "Nº OS",
                        "dt_ordem_servico_vma": "Data da OS",
                        "nm_orgao": "Secretaria",
                        "nm_razao_prest_norm": "Oficina Executora",
                        "vl_total_servicos_vma": st.column_config.NumberColumn("Valor Pago", format="R$ %,.2f"),
                        "de_servicos_vma_quebrado": "Descrição do Serviço"
                    },
                    column_order=[
                        "nu_ordem_servico_vma", "dt_ordem_servico_vma", "nm_orgao", 
                        "nm_razao_prest_norm", "vl_total_servicos_vma", "de_servicos_vma_quebrado"
                    ],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.success("✅ **Conformidade Contratual:** Nenhuma ordem de serviço paga pelo município foi identificada para veículos locados com cobertura de manutenção ativa.")

        # ── 🚨 CONDICIONAL EXCLUSIVA PARA O PANORAMA ESTADUAL ──────────────────
        if opcao_municipio == "Todos os Municípios":
            st.markdown("---")
            st.markdown("### 🏎️ Ranking de Custo Médio de Manutenção (R$ por Veículo)")
            if not df_manut_filtrado.empty and not df_veiculos_filtrado.empty:
                frota_por_municipio = df_veiculos_filtrado.groupby('nm_municipio')['cd_renavam_vm'].nunique()
                custo_por_municipio = df_manut_filtrado.groupby('nm_municipio')['vl_total_servicos_vma'].sum()
                ranking_series = (custo_por_municipio / frota_por_municipio).sort_values(ascending=False).dropna()

                df_custo_medio = ranking_series.reset_index()
                df_custo_medio.columns = ['nm_municipio', 'custo_medio_por_veiculo']
                df_top_10_medio = df_custo_medio.head(10)

                fig_custo_medio = px.bar(
                    df_top_10_medio,
                    x='nm_municipio',
                    y='custo_medio_por_veiculo',
                    title='Top 10 Municípios - Maior Custo Médio de Manutenção (R$ por veículo)',
                    labels={'nm_municipio': 'Município', 'custo_medio_por_veiculo': 'Custo Médio (R$/Veículo)'},
                    color='custo_medio_por_veiculo',
                    color_continuous_scale='YlOrRd',
                    text_auto='R$,.2f'
                )
                fig_custo_medio.update_layout(xaxis_tickangle=-45, template='plotly_white', yaxis_tickformat="R$,.2f", height=450, showlegend=False)
                st.plotly_chart(fig_custo_medio, use_container_width=True)
            else:
                st.info("Dados insuficientes para calcular o custo médio por veículo.")

            st.markdown("---")
            st.markdown("### 🔍 Matriz de Contexto e Avaliação de Anomalias (Z-Score)")
            st.write("Esta tabela analisa o comportamento de cada município em relação à média de custo por veículo de todo o Estado do Ceará.")

            if not df_manut_filtrado.empty and not df_veiculos_filtrado.empty:
                frota_por_municipio = df_veiculos_filtrado.groupby('nm_municipio')['cd_renavam_vm'].nunique()
                custo_por_municipio = df_manut_filtrado.groupby('nm_municipio')['vl_total_servicos_vma'].sum()
                ranking_custo_medio = (custo_por_municipio / frota_por_municipio).dropna()

                df_contexto = pd.DataFrame({
                    'Custo Total (R$)': custo_por_municipio,
                    'Qtd Frota': frota_por_municipio,
                    'Custo Médio (R$/Veículo)': ranking_custo_medio
                })

                custo_estado = df_manut_filtrado['vl_total_servicos_vma'].sum()
                df_contexto['% do Custo Estado'] = (df_contexto['Custo Total (R$)'] / custo_estado * 100) if custo_estado > 0 else 0.0

                media_estado = df_contexto['Custo Médio (R$/Veículo)'].mean()
                desvio_estado = df_contexto['Custo Médio (R$/Veículo)'].std()
                df_contexto['Z-Score'] = (df_contexto['Custo Médio (R$/Veículo)'] - media_estado) / desvio_estado if desvio_estado > 0 else 0.0

                def classifica_anomalia(z):
                    if z > 3: return '🚨 Crítico (Anomalia Extrema)'
                    if z > 2: return '⚠️ Alerta (Outlier)'
                    if z > 1: return '🧐 Suspeito'
                    return '✅ Normal'

                df_contexto['Avaliação'] = df_contexto['Z-Score'].apply(classifica_anomalia)
                df_contexto = df_contexto.sort_values('Custo Médio (R$/Veículo)', ascending=False).reset_index()

                st.dataframe(
                    df_contexto,
                    column_config={
                        "nm_municipio": "Município",
                        "Custo Total (R$)": st.column_config.NumberColumn("Custo Total", format="R$ %,.2f"),
                        "Qtd Frota": st.column_config.NumberColumn("Qtd Frota", format="%d"),
                        "Custo Médio (R$/Veículo)": st.column_config.NumberColumn("Custo Médio/Veículo", format="R$ %,.2f"),
                        "% do Custo Estado": st.column_config.NumberColumn("% Gasto Estado", format="%.2f %%"),
                        "Z-Score": st.column_config.NumberColumn("Z-Score", format="%.2f"),
                        "Avaliação": "Avaliação Estatística"
                    },
                    hide_index=True,
                    use_container_width=True
                )

                st.markdown("---")
                st.markdown("### 🗺️ Visão Espacial: Frota vs. Custo Total de Manutenção",
help="""
📊 **Como interpretar esta Análise Multidimensional (Bubble Chart):**

Este gráfico cruza três variáveis simultaneamente para identificar visualmente a eficiência do gasto de cada município:

* **Eixo X (`Qtd Frota`):** Mostra o tamanho da frota do município (quantidade de veículos únicos).
* **Eixo Y (`Custo Total (R$)`):** Mostra o volume financeiro bruto gasto em manutenção.
* **Tamanho da Bolha (`Custo Médio (R$/Veículo)`):** Quanto maior o diâmetro da esfera, maior é o custo médio pago para manter cada veículo individual daquela cidade.
* **Cores (Z-Score):** Refletem a gravidade do desvio padrão calculado na Matriz de Contexto.

🧐 **Como caçar anomalias neste gráfico?**
* **O Padrão Esperado:** Municípios deveriam formar uma linha diagonal ascendente regular. Quanto maior a frota (X), maior o custo total (Y), mantendo bolhas de tamanhos proporcionais.
* **O Alvo da Auditoria (Anomalias):** Procure por esferas que fujam da linha de tendência. Por exemplo, uma bolha gigante vermelha (`🚨 Crítico`) posicionada muito à esquerda (pouca frota) e muito no topo (gasto total altíssimo) denota um desvio severo de mercado que exige auditoria imediata de contratos.
""")
                
                # Mapeamento de cores idêntico ao da tabela para consistência visual
                mapa_cores_bubble = {
                    '🚨 Crítico (Anomalia Extrema)': '#d9534f',
                    '⚠️ Alerta (Outlier)': '#f0ad4e',
                    '🧐 Suspeito': '#5bc0de',
                    '✅ Normal': '#5cb85c'
                }

                df_bubble = df_contexto.dropna(subset=['Custo Médio (R$/Veículo)', 'Qtd Frota', 'Custo Total (R$)'])

                fig2 = px.scatter(
                    df_bubble, 
                    x='Qtd Frota',
                    y='Custo Total (R$)',
                    size='Custo Médio (R$/Veículo)',
                    color='Avaliação',
                    color_discrete_map=mapa_cores_bubble,
                    text='nm_municipio',
                    title='Dispersão: Frota vs. Custo Total de Manutenção por Município',
                    labels={
                        'Qtd Frota': 'Tamanho da Frota (veículos)',
                        'Custo Total (R$)': 'Custo Total de Manutenção (R$)',
                        'nm_municipio': 'Município',
                        'Avaliação': 'Avaliação Estatística'
                    },
                    custom_data=['Custo Médio (R$/Veículo)', 'Z-Score', 'Avaliação']
                )

                fig2.update_traces(
                    textposition='top center',
                    textfont=dict(size=9),
                    hovertemplate=(
                        '<b>%{text}</b><br>'
                        'Frota: %{x} veículos<br>'
                        'Custo Total: R$ %{y:,.2f}<br>'
                        'Custo Médio: R$ %{customdata[0]:,.2f}<br>'
                        'Z-Score: %{customdata[1]:.2f}<br>'
                        'Avaliação: %{customdata[2]}'
                        '<extra></extra>'
                    )
                )

                fig2.update_layout(
                    height=600,
                    plot_bgcolor='white',
                    yaxis=dict(showgrid=True, gridcolor='#eeeeee', tickprefix='R$ ', tickformat=',.0f'),
                    xaxis=dict(showgrid=True, gridcolor='#eeeeee'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )
                
                st.plotly_chart(fig2, use_container_width=True)

            else:
                st.info("Dados insuficientes para gerar o gráfico de dispersão espacial.")
        
        else:
            # Feedback visual se um município específico for selecionado
            st.markdown("---")
            st.info(f"💡 As análises macroestatísticas do Estado (Custo Médio, Matriz Z-Score e Dispersão Frota vs Gasto) ficam ocultas quando um município individual é selecionado.")

        # ── Triagem e Retenção Financeira ─────────────────────────────────────
        st.markdown("---")
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