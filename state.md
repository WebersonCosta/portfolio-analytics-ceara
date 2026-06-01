# State - Análise de Dados de Manutenção (Frota Municipal)

## 1. Resumo do Status do Projeto
* **Fase Atual:** Nova Fase - Dashboard de Inteligência e Geolocalização.
* **Última Atualização:** Maio de 2026.
* **Situação Geral:** **[100% CONCLUÍDO]** Integração do De-Para IBGE via API e desenvolvimento da infraestrutura básica do Dashboard Streamlit concluídos com sucesso. O app foi lançado localmente e executa o pipeline em tempo real com filtros reativos.

---

## 2. Marco de Entregas (Roadmap Checklist)

### 2.1. Análise Exploratória e Estatística da Frota
* [x] Levantar o perfil descritivo da frota municipal por vínculo (Próprio, Locado, Cedido), idade média e situação real.
* [x] Mapear a volumetria e distribuição geográfica (por `cd_municipio`) dos gastos de manutenção em 2025.

### 2.2. Painel de Auditoria de Riscos e Anomalias
* [x] **Ranking de Prestadores de Serviço:** Identificação de monopólios de execução (Caso detectado em Caucaia).
* [x] **Análise de Alertas Textuais:** Medição do impacto financeiro de OSs com descrições curtas e agrupadas.
* [x] **Detecção de Outliers Financeiros:** Implementação e cruzamento de Isolation Forest, IQR e Z-Score.
* [x] **Estudo da Quarentena:** Levantamento do descompasso financeiro total retido na triagem do pipeline.
* [x] **Integração de API de Terceiros (TCE-CE):** Mapeamento de-para de código do município para códigos IBGE de 7 e 6 dígitos.
* [x] **Infraestrutura do Dashboard (Streamlit):** Interface interativa reativa com filtros de municípios, KPIs e rankings de prestadores.

---

## 3. Descobertas Críticas da Auditoria (Métricas de Estado)

Os outputs do notebook revelaram três vulnerabilidades críticas na execução da despesa pública da frota em 2025:

| Tipo de Anomalia | Impacto Detectado | Diagnóstico Técnico |
| :--- | :--- | :--- |
| **Monopólio de Execução** | R$ 8.000.000,00 concentrados em um único prestador em Caucaia. | Empresa *7SERV GESTAO DE BENEFICIOS LTDA* centraliza os pagamentos, indicando um modelo de gerenciamento de frota terceirizado que mascara as oficinas executoras finais. |
| **Falta de Transparência** | R$ 17.887.318,64 pagos em 12.887 OSs com descrições curtíssimas. | Alto volume de empenhos aprovados com descrições de texto com menos de 25 caracteres (`alerta_desc_curta = True`), impedindo o controle social da peça trocada. |
| **Descompasso Orçamentário** | R$ 9.900.766,55 em divergência financeira (Soma das OS vs Valor Empenhado). | **Quarentena Crítica:** Apenas 18 Notas de Empenho acumulam R$ 5,4 milhões em descompasso severo (acima de R$ 100 mil por NE), apontando falha grave de liquidação em poucos contratos. |

---

## 4. Arquivos Gerados e Persistidos (`output/`)
O notebook executou as diretrizes de design e persistiu os seguintes relatórios interativos HTML de forma autônoma:
1. `output/analise_situacao_frota.html` — Panorama descritivo de uso e sucatas.
2. `output/distribuicao_idade_frota.html` — Boxplot analítico (limpo de outliers centenários da frota).
3. `output/top_municipios_gastos_manutencao.html` — Volumetria de despesa por cidade, liderada isoladamente por Caucaia.
4. `output/top_prestadores_caucaia.html` — Gráfico horizontal demonstrando a concentração absoluta da *7SERV*.
5. `output/analise_outliers_modelos.html` — Gráfico de dispersão cruzando Isolation Forest, IQR e Z-Score.
6. `output/analise_impacto_quarentena.html` — Gráfico de rosca demonstrando o impacto financeiro da triagem.
7. `output/empenhos_quarentena_critica.csv` — Listagem com as 18 Notas de Empenho críticas retidas na quarentena para auditoria de campo.

---

## 5. Próximos Passos Sugeridos para a Próxima Sprint (Infraestrutura do Dashboard)
1. [x] Consolidar as visualizações Plotly em uma interface/dashboard centralizada em Python (usando Streamlit).
2. [ ] Enriquecer as Notas de Empenho críticas no relatório de campo com informações complementares de CNPJ e telefone cadastrados dos prestadores.
3. [ ] Criar o mapa de calor coroplético interativo do Ceará (`px.choropleth`) integrado com o GeoPandas para geolocalização dos gastos.