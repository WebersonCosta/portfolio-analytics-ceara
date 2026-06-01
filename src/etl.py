# src/etl.py

import unicodedata
import pandas as pd
from src.config import (
    ANO, 
    MES_INICIO, 
    MES_FIM,

    ARQUIVOS,

    SEP_CSV, 
    DTYPE_BASE, 

    PRIORIDADE_MODO_CONTRATO, 
     
)


def normaliza_texto(texto):
    """Remove acentuação inconsistente causada por encoding quebrado."""
    if pd.isna(texto):
        return texto
    return (
        unicodedata.normalize('NFKD', str(texto)) # Normalização NFKD decompoem caracteres especiais: 
        # 'ação ' -> 'a + c + cedilha + a + til + o '
        .encode('ascii', errors='ignore') # Transforma em bytes de ASCII que não reconhece caracteres especiais -> b'acao ' 
        .decode('ascii') # Transofrma de volta em string: b'acao ' -> 'acao '
        .upper() # Transforma tudo em maiúsculo: 'acao ' -> 'ACAO '
        .strip() # Remove espaços em branco no começo e no final da string: 'ACAO ' -> 'ACAO'
    )

def normaliza_doc(valor):
    if pd.isna(valor):
        return None
    return str(valor).strip().replace('.','').replace('/','').replace('-','')

def carrega_bases():
    """Carrega e faz limpeza inicial das quatro bases do SIM."""
    df_veiculos = pd.read_csv(ARQUIVOS['veiculos'], sep=SEP_CSV, dtype=DTYPE_BASE, engine='python')
    df_veiculos.columns = df_veiculos.columns.str.replace('"','').str.strip()
    
    df_manut_raw = pd.read_csv(ARQUIVOS['manutencoes'], sep=SEP_CSV, dtype=DTYPE_BASE, engine='python')
    df_manut_raw.columns = df_manut_raw.columns.str.replace('"','').str.strip()
    df_manut_raw = df_manut_raw[
        pd.to_datetime(df_manut_raw['dt_ordem_servico_vma'], errors='coerce')
        .dt.year == ANO
    ].copy()

    df_locados = pd.read_csv(ARQUIVOS['locados'], sep=SEP_CSV, dtype=DTYPE_BASE, engine='python')
    df_locados.columns = df_locados.columns.str.replace('"','').str.strip()
    df_locados = df_locados[
        (df_locados['dt_ref_vl'] >= MES_INICIO) &
        (df_locados['dt_ref_vl'] <= MES_FIM)
    ].copy()

    df_cedidos = pd.read_csv(ARQUIVOS['cedidos'], sep=SEP_CSV, dtype=DTYPE_BASE, engine='python')
    df_cedidos.columns = df_cedidos.columns.str.replace('"','').str.strip()
    df_cedidos = df_cedidos[
        (df_cedidos['dt_ref_vc'] >= MES_INICIO) &
        (df_cedidos['dt_ref_vc'] <= MES_FIM)
    ].copy()

    return df_veiculos, df_manut_raw, df_locados, df_cedidos

def normaliza_bases(df_veiculos, df_manut_raw, df_locados):
    """Aplica normalização de texto, documentos e CONVERSÃO NUMÉRICA."""
    
    # 1. Normalização de IDs e Municípios 
    for df in [df_veiculos, df_manut_raw, df_locados]:
        df['cd_renavam_vm'] = df['cd_renavam_vm'].astype(str).str.strip()
        if 'cd_municipio' in df.columns:
            df['cd_municipio'] = df['cd_municipio'].astype(str).str.strip()

    cols_datas = ['dt_inclusao_vd', 'dt_baixa_vbd']
    for col in cols_datas:
        if col in df_manut_raw.columns:
            df_manut_raw[col] = pd.to_datetime(df_manut_raw[col], errors='coerce')

    # 2. CONVERSÃO FINANCEIRA
    # Lista de colunas que precisam virar número na base de manutenção
    cols_financeiras = ['vl_total_servicos_vma', 'vl_empenhado_ne', 'valor_liquidado', 'valor_pago']
    
    for col in cols_financeiras:
        if col in df_manut_raw.columns:
            df_manut_raw[col] = (
                df_manut_raw[col]
                .astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
                .str.replace('nan', '0')
                .astype(float)
            )


    # 3. Normalização de Textos e Docs (o que você já tinha)
    df_manut_raw['nm_razao_prest_norm'] = df_manut_raw['nm_razao_prest_serv_vma'].apply(normaliza_texto)
    df_manut_raw['nu_doc_prest_norm']   = df_manut_raw['nu_doc_prest_serv_vma'].apply(normaliza_doc)
    df_locados['nm_locador_norm']       = df_locados['nm_locador_vl'].apply(normaliza_texto)
    df_locados['nu_doc_locador_norm']   = df_locados['nu_doc_locador_vl'].apply(normaliza_doc)
    df_veiculos['nm_proprietario_vm']   = df_veiculos['nm_proprietario_vm'].apply(normaliza_texto)
    df_veiculos['nu_doc_proprietario_vm'] = df_veiculos['nu_doc_proprietario_vm'].apply(normaliza_doc)


    # 4. Padronização de Nomes Mestres (Evita duplicidade nos rankings)
    mapa_nomes_prestadores = (
        df_manut_raw.groupby('nu_doc_prest_norm')['nm_razao_prest_norm']
        .agg(lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0])
        .to_dict()
    )

    # Aplicamos o nome mestre de volta à base
    df_manut_raw['nm_razao_prest_norm'] = df_manut_raw['nu_doc_prest_norm'].map(mapa_nomes_prestadores)

    return df_veiculos, df_manut_raw, df_locados

def enriquece_veiculos(df_veiculos, ano):
    """
    Calcula a frota ativa real e refina o status baseado na finalidade.
    Versão ultra-segura contra colunas ausentes.
    """
    
    col_inc = 'dt_inclusao_vd'
    col_baix = 'dt_baixa_vbd'
    col_fin = 'finalidade_vei'

    # 1. Lógica de Frota Ativa (Só roda se as datas existirem)
    if col_inc in df_veiculos.columns and col_baix in df_veiculos.columns:
        df_veiculos[col_inc] = pd.to_datetime(df_veiculos[col_inc], errors='coerce')
        df_veiculos[col_baix] = pd.to_datetime(df_veiculos[col_baix], errors='coerce')

        df_veiculos['is_ativo_2025'] = (
            (df_veiculos[col_inc].dt.year.fillna(0) <= ano) &
            ((df_veiculos[col_baix].isna()) | (df_veiculos[col_baix].dt.year >= ano))
        )
    else:
        df_veiculos['is_ativo_2025'] = True
        print(f"ℹ️ Info: Datas de movimentação não encontradas. Frota total considerada ativa.")

    # 2. Refinamento da Situação Real (Só roda se a Finalidade existir)
    if col_fin in df_veiculos.columns:
        df_veiculos['finalidade_norm'] = df_veiculos[col_fin].apply(normaliza_texto)
        
        def define_status_real(row):
            final = str(row['finalidade_norm'])
            if any(t in final for t in ['PATIO', 'INSERVIVEL', 'SUCATA']): return 'Sucata'
            if any(t in final for t in ['GARAGEM', 'OCIOSO']): return 'Ocioso'
            if row.get('is_ativo_2025') == False: return 'Baixado/Inativo'
            return 'Em Operação'

        df_veiculos['situacao_real'] = df_veiculos.apply(define_status_real, axis=1)
    else:
        df_veiculos['situacao_real'] = 'Em Operação (Finalidade não informada)'

    # 3. Cálculo de Idade
    if 'nu_ano_fabricacao_vm' in df_veiculos.columns:
        # Convertemos para numérico para tratar NaNs e inconsistências de tipos
        df_veiculos['nu_ano_fabricacao_vm'] = pd.to_numeric(df_veiculos['nu_ano_fabricacao_vm'], errors='coerce')
        
        # Corrigimos anos de fabricação impossíveis (idade > 50 anos) para ausente
        df_veiculos.loc[(ano - df_veiculos['nu_ano_fabricacao_vm']) > 50, 'nu_ano_fabricacao_vm'] = pd.NA
        
        df_veiculos['idade_veiculo'] = (ano - df_veiculos['nu_ano_fabricacao_vm']).clip(lower=0)
    else:
        df_veiculos['idade_veiculo'] = 0
    
    return df_veiculos

def enriquece_locados(df_locados):
    """Identifica aditivos e deduplica por veículo/mês."""
    df_locados['eh_aditivo']      = df_locados['nu_contrato_original'].notna()
    df_locados['nu_contrato_pai'] = df_locados['nu_contrato_original'].fillna(
        df_locados['nu_contrato']
    )
    df_locados['prioridade'] = df_locados['modo_contrato'].map(
        PRIORIDADE_MODO_CONTRATO
    ).fillna(0)
    df_locados = (
        df_locados
        .sort_values(by=['prioridade', 'dt_ref_vl'], ascending=False)
        .drop_duplicates(subset=['cd_renavam_vm', 'dt_ref_vl'], keep='first')
        .drop(columns='prioridade')
    )
    return df_locados

def deduplica_os(df_manut_raw):
    """Deduplica a tabela de manutenções para nível de OS."""
    CHAVE_OS = ['cd_municipio', 'cd_renavam_vm', 'nu_ordem_servico_vma']
    return (
        df_manut_raw
        .sort_values('vl_total_servicos_vma', ascending=False)
        .drop_duplicates(subset=CHAVE_OS, keep='first')
        .copy()
    )

def agrega_por_ne(df_manut_os):
    """Agrega dados financeiros no nível de Nota de Empenho com Chave Composta."""
    CHAVE_NE = [
        'cd_municipio',
        'dt_versao_orc',
        'cd_orgao',
        'cd_unid_orc',
        'dt_emissao_ne',
        'nu_nota_empenho'
    ]
    
    # Verificação de segurança: só agrupa se todas as colunas existirem
    cols_presentes = [c for c in CHAVE_NE if c in df_manut_os.columns]
    
    return (
        df_manut_os
        .groupby(cols_presentes)
        .agg(
            nm_municipio     = ('nm_municipio', 'first'),
            nm_orgao         = ('nm_orgao', 'first'),
            nm_unid_orc      = ('nm_unid_orc', 'first'),
            vl_empenhado_ne  = ('vl_empenhado_ne', 'first'),
            valor_liquidado  = ('valor_liquidado', 'first'),
            valor_pago       = ('valor_pago', 'first'),
            soma_os          = ('vl_total_servicos_vma', 'sum'),
            qtd_os           = ('nu_ordem_servico_vma', 'nunique')
        )
        .reset_index()
    )
# Adicione no topo do arquivo ou junto com as outras funções auxiliares
def detectar_agrupamento(texto):
    """Identifica se uma OS menciona múltiplos veículos de forma inteligente."""
    if pd.isna(texto): 
        return False
    
    texto = str(texto).upper()
    
    # 1. Termos que indicam agrupamento "de cara" (Plural ou Coletivos)
    termos_diretos = ['PLACAS', 'PARA OS VEICULOS', 'PARA OS ONIBUS',  'TODA A FROTA']
    if any(termo in texto for termo in termos_diretos):
        return True
    
    # 2. Regra da Repetição: 'PLACA' precisa aparecer 2 vezes ou maisW
    if texto.count('PLACA') >= 2:
        return True
        
    return False

def enriquece_manutencoes(df_manut_os):
    """Adiciona colunas de diagnóstico à base de manutenções."""
    # Aplica a detecção de agrupamento
    df_manut_os['alerta_agrupamento'] = df_manut_os['de_servicos_vma'].apply(detectar_agrupamento)
    
    # (Ex: descrições com menos de 20 caracteres)
    df_manut_os['alerta_desc_curta'] = df_manut_os['de_servicos_vma'].str.len() < 25
    
    return df_manut_os

def carrega_de_para_ibge():
    """
    Consome a API de dados abertos do TCE-CE para mapear o cd_municipio (3 dígitos)
    para o código oficial do IBGE de 7 e 6 dígitos.
    Retorna um DataFrame com a correlação.
    """
    import requests
    url = "https://api-dados-abertos.tce.ce.gov.br/sim/municipios"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        elements = data.get("elements", [])
        df = pd.DataFrame(elements)
        
        # Filtrar registros sem código IBGE (como TCM '001')
        df = df.dropna(subset=["codigo_municipio_ibge"]).copy()
        
        # Renomear e formatar as colunas
        df = df.rename(columns={"codigo_municipio": "cd_municipio"})
        df["cd_municipio"] = df["cd_municipio"].astype(str).str.strip().str.zfill(3)
        df["codigo_municipio_ibge"] = df["codigo_municipio_ibge"].astype(str).str.strip()
        
        # Gerar a versão de 6 dígitos
        df["codigo_municipio_ibge_6"] = df["codigo_municipio_ibge"].str[:6]
        
        # Retorna apenas as colunas relevantes
        return df[["cd_municipio", "nome_municipio", "codigo_municipio_ibge", "codigo_municipio_ibge_6"]]
        
    except Exception as e:
        print(f"⚠️ Erro ao carregar dados da API do TCE-CE: {e}")
        # Retorna um DataFrame vazio estruturado para evitar erros em cascata no merge
        return pd.DataFrame(columns=["cd_municipio", "nome_municipio", "codigo_municipio_ibge", "codigo_municipio_ibge_6"])