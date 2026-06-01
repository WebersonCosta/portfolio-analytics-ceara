# src/quarentena.py

import pandas as pd
from src.config import (
    TOLERANCIA_FLOAT, LIMIAR_INVESTIGACAO, LIMIAR_QUARENTENA
)

def aplica_quarentena(df_manut_os):
    # 1. Agrupamento (igual ao seu)
    soma_os_por_ne = (
        df_manut_os
        .groupby(['cd_municipio', 'nu_nota_empenho'])
        .agg(
            soma_os = ('vl_total_servicos_vma', 'sum'),
            vl_empenhado_ne = ('vl_empenhado_ne', 'first')
        )
        .reset_index()
    )

    soma_os_por_ne['dif'] = (soma_os_por_ne['soma_os'] - soma_os_por_ne['vl_empenhado_ne']).round(2)

    soma_os_por_ne.loc[soma_os_por_ne['dif'] <= TOLERANCIA_FLOAT, 'dif'] = 0

    # 2. Definindo o Status (Vetorizado)
    import numpy as np
    condicoes = [
        (soma_os_por_ne['dif'] > LIMIAR_QUARENTENA),
        (soma_os_por_ne['dif'] > LIMIAR_INVESTIGACAO)
    ]
    escolhas = ['Quarentena', 'Investigar']
    soma_os_por_ne['status_ne'] = np.select(condicoes, escolhas, default='OK')

    # 3. Levando o status de volta para o DataFrame original via MERGE
    # Isso é MUITO mais rápido que usar .apply()
    df_manut_os = df_manut_os.merge(
        soma_os_por_ne[['cd_municipio', 'nu_nota_empenho', 'status_ne']], 
        on=['cd_municipio', 'nu_nota_empenho'], 
        how='left'
    )

    # 4. Criando os DataFrames de saída
    df_quarentena   = df_manut_os[df_manut_os['status_ne'] == 'Quarentena'].copy()
    df_investigacao = df_manut_os[df_manut_os['status_ne'] == 'Investigar'].copy()
    df_valido       = df_manut_os[df_manut_os['status_ne'] == 'OK'].copy()

    # Prepara os retornos detalhados (opcional, para os seus relatórios de auditoria)
    ne_quarentena = soma_os_por_ne[soma_os_por_ne['status_ne'] == 'Quarentena'].copy()
    ne_investigacao = soma_os_por_ne[soma_os_por_ne['status_ne'] == 'Investigar'].copy()

    return df_valido, df_investigacao, df_quarentena, ne_quarentena, ne_investigacao