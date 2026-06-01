# Requirements - Análise de Dados de Manutenção (Frota Municipal)

## 1. Visão Geral do Projeto
Este projeto realiza o pipeline de Extração, Transformação, Carga (ETL) e Auditoria de dados da frota de veículos municipais e seus respectivos gastos com manutenção no ano de 2025. O foco principal é identificar anomalias, inconsistências financeiras e indícios de irregularidades contratuais ou operacionais em dados públicos.

## 2. Arquitetura do Projeto
O projeto segue a estrutura de diretórios abaixo:

Analise de Dados de Manutencao - Frota Municipal/
│
├── dados/                       # Arquivos CSV originais (fontes de dados)
│   ├── veiculos_cedidos.csv      
│   ├── veiculos_locados.csv
│   ├── veiculos_manutencao.csv
│   └── veiculos.csv
├── notebook/                    # Arquivos de análise exploratória e insights
│   └── analise_manutencao_veiculos.ipynb
├── output/                      # Dados consolidados e limpos exportados
├── src/                         # Código-fonte modularizado
│   ├── config.py                # Configurações globais e mapeamento de caminhos
│   ├── etl.py                   # Script principal de Extração, Transformação e Carga
│   └── quarentena.py            # Regras e isolamento de dados inconsistentes
└── requirements.md              # Documentação de contexto (GSD)

---

## 3. O Que o Projeto Já Faz (Arquitetura Atual)

O ecossistema possui três módulos principais (`src/`) totalmente operacionais, parametrizados pelo `src/config.py`:

### 3.1. Configurações Globais (`src/config.py`)
* **Filtro Temporal:** Restringe a análise ao ano de 2025 (Meses: 202501 a 202512).
* **Ingestão Customizada:** Define o separador proprietário `¬` e trata tipos complexos (ex: Renavam e Código do Município como Strings para evitar perda de zeros à esquerda).
* **Regras de Negócio e Limiares:** * Tolerância de arredondamento financeiro ($ 0.01).
    * Réguas de corte para divergências em Notas de Empenho: Investigação (> $10.000) e Quarentena (>$ 100.000).
    * Parâmetros estatísticos pré-configurados para detecção de Outliers (Z-Score = 3.0, IQR = 1.5, Contaminação Isolation Forest = 5%).
    * Mapeamento de prioridades de aditivos contratuais, situações da frota e termos textuais suspeitos (ex: "PÁTIO", "SUCATA").

### 3.2. Engine de ETL (`src/etl.py`)
* **Saneamento de Strings:** Função `normaliza_texto` que corrige quebras de encoding via decomposição NFKD, remove acentos, remove espaços extras e padroniza em caixa alta.
* **Normalização de Documentos:** Função `normaliza_doc` que limpa pontuações de CNPJ/CPF.
* **Tratamento de Bases:**
    * Carrega 4 fontes (`veiculos`, `manutencoes`, `locados` e `cedidos`).
    * Aplica tipagem financeira rigorosa (removendo pontos de milhar, convertendo vírgulas em pontos e tratando NaNs como zero).
    * **Deduplicação Inteligente de Nomes:** Cria um dicionário mestre baseado na moda (`.mode()`) da Razão Social por CNPJ para evitar que o mesmo prestador apareça duplicado em rankings devido a erros de digitação.
* **Enriquecimento e Regras de Negócio:**
    * `enriquece_veiculos`: Determina a frota ativa real em 2025 cruzando datas de inclusão/baixa, calcula a idade do veículo e infere uma `situacao_real` baseada nas strings da finalidade declarada.
    * `enriquece_locados`: Identifica contratos aditivos e aplica uma regra de prioridade (`PRIORIDADE_MODO_CONTRATO`) para remover duplicidades de veículos locados no mesmo mês, retendo apenas o contrato mais relevante.
    * `deduplica_os`: Garante a unicidade da tabela de manutenções ao nível de Ordem de Serviço (OS).
    * `enriquece_manutencoes`: Cria flags de diagnóstico através de IA Heurística (`alerta_agrupamento` para identificar se uma única OS englobou vários veículos/ônibus na mesma descrição, e `alerta_desc_curta` para descrições com menos de 25 caracteres).

### 3.3. Subsistema de Triagem e Qualidade (`src/quarentena.py`)
* **Auditoria Financeira:** Agrupa as OSs por Nota de Empenho (NE) e calcula a diferença (`dif`) entre a soma das ordens de serviço e o valor efetivamente empenhado na NE.
* **Isolamento de Dados (Vetorizado via NumPy):** Divide a base de manutenção de forma performática em três sub-datasets:
    1.  `df_valido`: Registros com inconsistências dentro do limite tolerável.
    2.  `df_investigacao`: Divergências moderadas (acima de $ 10.000).
    3.  `df_quarentena`: Inconsistências graves (acima de $ 100.000) que precisam ser isoladas para não distorcer as análises estatísticas gerais.

### 3.4. Estado Atual do Notebook (Dados Carregados)
* **Status de Ingestão:** Ambiente preparado, caminhos de diretórios validados e bibliotecas de visualização (`seaborn`, `plotly`) importadas.
* **Consistência de Dados:** Integração perfeita entre bases. 100% dos veículos que sofreram manutenção constam na base de cadastro (Limbo = 0%).
* **Dataframes Disponíveis:**
    * `df_veiculos`: 11.486 registros | Coluna chave: `tp_vinculacao_vm`, `idade_veiculo`, `situacao_real`.
    * `df_manut_os`: 51.437 registros (pós-quarentena) | Coluna chave: `vl_total_servicos_vma`, `nm_razao_prest_norm`, `alerta_agrupamento`, `alerta_desc_curta`.
    * `df_locados`: 6.429 registros (deduplicados por aditivo/mês).
    * `df_cedidos`: 81 registros.

---

## 4. Próximos Passos: O Que Falta Fazer (Escopo do Jupyter Notebook)
*O objetivo agora é utilizar o arquivo `notebook/analise_manutencao_veiculos.ipynb` para consumir as bases tratadas e gerar os seguintes relatórios e visuais:*

### 4.1. Análise Exploratória e Estatística da Frota
* [ ] Levantar o perfil descritivo da frota municipal por vínculo (Próprio, Locado, Cedido), idade média e situação real.
* [ ] Mapear a volumetria e distribuição geográfica (por `cd_municipio`) dos gastos de manutenção em 2025.

### 4.2. Painel de Auditoria de Riscos e Anomalias
* [ ] **Ranking de Prestadores de Serviço:** Identificar os maiores recebedores de volume financeiro (usando o nome mestre limpo pelo ETL).
* [ ] **Análise de Alertas Textuais:** Cruzar o volume financeiro gasto em OS que possuem `alerta_desc_curta` ou `alerta_agrupamento` ativados para medir o impacto de descrições genéricas.
* [ ] **Detecção de Outliers Financeiros:** Aplicar as métricas de Z-Score, IQR e testar o algoritmo de Machine Learning *Isolation Forest* (usando os parâmetros do `config.py`) para listar manutenções com valores severamente discrepantes.
* [ ] **Estudo da Quarentena:** Plotar o volume total de recursos públicos retidos nos DataFrames de investigação e quarentena para apresentar o diagnóstico do descompasso entre Empenhos e Execuções de OS.

### 4.3. Diretrizes de Output e Visualização
* **Engine Visual:** Utilizar exclusivamente **Plotly (Express/Objects)** para garantir interatividade nas auditorias.
* **Persistência:** Todos os gráficos gerados devem ser exportados em formato HTML autônomo para o diretório `output/` utilizando o método `.write_html()`.

## 5. Nova Fase: Dashboard de Inteligência e Geolocalização

### 5.1. Integração de API de Terceiros (TCE-CE)
* **Endpoint:** `https://api-dados-abertos.tce.ce.gov.br/sim/municipios`
* **Estratégia de DE-PARA:** O sistema deve consumir a API do tribunal para mapear o código interno de 3 dígitos (`cd_municipio`) para o código oficial do IBGE de 7 dígitos (`codigo_municipio_ibge`), permitindo a compatibilidade com mapas geográficos.
* **Resiliência:** Implementar tratamento de exceções (try/except) e timeout na requisição para evitar travamentos caso a API esteja fora do ar.

### 5.2. Infraestrutura do Dashboard (Streamlit + GeoPandas)
* **Framework Principal:** Streamlit para a interface web.
* **Geolocalização:** GeoPandas para manipulação da malha espacial do Ceará e `px.choropleth` do Plotly para renderização do mapa de calor interativo.
* **Componentes Interativos Almejados:**
    * [ ] Mapa do Ceará interativo colorido pelo volume total de gastos com manutenção em 2025.
    * [ ] Barra de pesquisa/seleção de município para detalhamento automático (filtros reativos).
    * [ ] Exibição automática do Top Prestador do município selecionado (ex: evidenciando casos de concentração como a *7SERV* em Caucaia).