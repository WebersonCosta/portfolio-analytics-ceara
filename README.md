# 🚚 Auditoria e Análise de Dados de Manutenção (Frota Municipal - Ceará 2025)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Streamlit-red.svg)](https://streamlit.io/)
[![Licença](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Este repositório contém uma solução completa de engenharia de dados, detecção de anomalias por Machine Learning e auditoria de gastos públicos direcionada à frota de veículos municipais do Ceará no ano de 2025. 

O projeto consome dados brutos de contratos e ordens de serviço (OS) de manutenção e entrega um **Dashboard de Inteligência e Geolocalização** interativo, desenvolvido em Streamlit, para auxiliar órgãos de controle social e auditoria de campo.

---

## 🔎 O Problema Analítico: A Auditoria dos R$ 111,4 Milhões

Em 2025, os municípios do Ceará empenharam e liquidaram um total de **R$ 111,4 milhões** em ordens de serviço válidas para manutenção de veículos públicos (próprios, locados e cedidos). Diante desse montante expressivo de recursos públicos, nossa equipe estruturou um pipeline automatizado de auditoria para identificar padrões incomuns de contratação, desvios fiscais e indícios de fraude.

As principais vulnerabilidades críticas reveladas pelo sistema foram:
1. **Monopólio de Execução (Concentração de Mercado):** Identificação de prestadores centralizando parcelas milionárias de contratos em municípios específicos. Em Caucaia, por exemplo, detectou-se que a empresa *7SERV GESTÃO DE BENEFÍCIOS LTDA* concentrou cerca de **R$ 8,0 milhões** dos gastos de manutenção do município, evidenciando um modelo terceirizado de gestão de frotas que omite o prestador final.
2. **Falta de Transparência Crítica (Descrições Curtas):** Cerca de **R$ 17,8 milhões** distribuídos em 12.887 OSs foram liberados com descrições com menos de 25 caracteres (ex: "Serviço realizado", "Reparo geral"), o que impede o controle social e a verificação do que de fato foi feito ou trocado no veículo.
3. **Descompasso Orçamentário e Triagem Financeira (Quarentena):** Divergência acumulada de **R$ 9,9 milhões** entre os valores faturados em OSs e as respectivas Notas de Empenho (NE). Na triagem, identificamos que apenas 18 Notas de Empenho apresentaram divergências acima de R$ 100 mil cada, retendo **R$ 5,4 milhões** sob suspeição severa (quarentena crítica) para investigação de campo.

---

## ⚙️ Engenharia da Solução

O sistema é construído de forma modular com quatro componentes principais localizados na pasta `src/`:

```
Analise de Dados de Manutencao - Frota Municipal/
│
├── dados/                       # Bases originais comprimidas (CSV, separador "¬")
├── src/                         # Arquivos fonte em Python
│   ├── app.py                   # Frontend Streamlit e visualizações Plotly
│   ├── config.py                # Regras de negócio, parâmetros estatísticos e caminhos
│   ├── etl.py                   # Engine de Extração, Transformação e Carga
│   └── quarentena.py            # Regras financeiras e isolamento de dados
└── README.md                    # Documentação principal
```

### 1. Engine de ETL (`src/etl.py`)
- **Sanitização de Strings:** Normalização de textos via decomposição Unicode NFKD para remoção automática de acentos, caracteres especiais e padronização em caixa alta.
- **Normalização de CNPJ/CPF:** Padronização e remoção de pontuações de documentos de fornecedores.
- **Deduplicação por Moda:** Criação de um dicionário mestre de Razão Social por CNPJ utilizando a moda (`.mode()`) estatística para evitar duplicidades no ranking geradas por erros de digitação.
- **Deduplicação de Contratos Locados:** Eliminação de aditivos contratuais redundantes baseada em regras de prioridade temporal e modal definidos no `config.py`.

### 2. Triagem e Qualidade de Dados (`src/quarentena.py`)
- **Auditoria Financeira:** Agrupa gastos de OSs por Nota de Empenho e calcula a diferença em relação ao valor empenhado.
- **Vetorização com NumPy:** Separa os dados de manutenção em três sub-datasets com base na gravidade do descompasso:
  - `df_valido`: Inconsistências dentro do limite tolerável ($ 0.01).
  - `df_investigacao`: Diferenças moderadas (R$ 10k a R$ 100k).
  - `df_quarentena`: Divergências críticas (> R$ 100k) isoladas para evitar distorções estatísticas.

### 3. Integração com APIs Governamentais
- **DE-PARA IBGE (TCE-CE):** Consumo dinâmico da API aberta do Tribunal de Contas do Estado do Ceará (`https://api-dados-abertos.tce.ce.gov.br/sim/municipios`) para converter o código interno de 3 dígitos das cidades no código oficial do IBGE de 6 e 7 dígitos.
- **Resiliência e Timeout:** Tratamento rigoroso de exceções e timeouts de rede para assegurar a continuidade do pipeline mesmo em caso de instabilidade dos servidores do TCE.

### 4. Modelos Antifraude (Detecção de Outliers)
- **Isolation Forest (Machine Learning):** Algoritmo não-supervisionado treinado nas ordens de serviço válidas usando o limiar de contaminação definido centralizadamente em `config.py`.
- **Filtros Estatísticos IQR e Z-Score:** Cruzamento matemático clássico (IQR = 1.5 e Z-Score = 3.0) para gerar um "Score de Suspeição" integrado (0 a 3 indicando quantos modelos classificaram a OS como anômala).

---

## 🖥️ Dashboard Streamlit em Abas

O painel central de geolocalização e auditoria é estruturado em **3 abas de navegação** alimentadas de forma reativa de acordo com a seleção de filtros na barra lateral:

### Tab 1: Perfil da Frota
- **Situação Real da Frota:** Gráfico de barras (`plotly_express`) demonstrando a distribuição ativa por finalidade do veículo.
- **Distribuição de Idade por Vínculo:** Gráfico Boxplot interativo comparando a idade média e a dispersão dos veículos próprios, locados e cedidos.

### Tab 2: Análise de Gastos e Prestadores
- **Top 10 Prestadores de Serviço:** Gráfico de barras horizontal demonstrando quais empresas centralizam os maiores aportes financeiros.
- **Top 20 Municípios por Volume de Gastos:** Identificação visual rápida das administrações com maior fatura de serviços contratados.
- **Diagnóstico de Transparência:** Métricas reativas que isolam e mostram o volume financeiro envolvido em OSs com descrições curtas e descrições agrupadas.
- **Dados de Geolocalização (IBGE):** Visualização do De-Para oficial com o IBGE obtido da API do TCE-CE.

### Tab 3: Modelos Antifraude & Quarentena
- **Detecção de Outliers Financeiros:** Gráfico de dispersão interativo contendo as 500 Ordens de Serviço mais suspeitas de acordo com o cruzamento dos modelos Isolation Forest, Z-Score e IQR.
- **Rosca de Retenção da Quarentena:** Gráfico de rosca dinâmico com o total de recursos retidos na triagem orçamentária e uma tabela detalhada com as notas de empenho críticas para auditoria prioritária em campo.

---

## 👥 Guia de Replicação para a Equipe (Provisório)

> [!NOTE]
> **Aviso para a equipe:** Este guia de replicação é temporário e será removido na entrega final do repositório.

Para rodar e testar o projeto na sua máquina local, siga os passos abaixo:

### Pré-requisitos
- Python instalado (versão 3.9 ou superior recomendada).
- Conexão ativa com a internet para carregar os dados de Geolocalização (GeoJSON) e a API do TCE-CE no primeiro carregamento.

### Passo a Passo

1. **Clonar/Navegar para o repositório:**


2. **Criar e Ativar Ambiente Virtual (Recomendado):**
   No PowerShell:
   ```powershell
   python -m venv venv
   ```
   ```powershell
   venv\Scripts\Activate
   ```

3. **Instalar Dependências:**
   Instale as bibliotecas necessárias para rodar o pipeline e a interface:
   ```bash
   pip install pandas numpy scikit-learn streamlit plotly requests
   ```

4. **Verificar os Arquivos de Dados:**
   Certifique-se de que a pasta `dados/` no diretório raiz contém os quatro arquivos originais:
   - `veiculos.csv`
   - `veiculos_manutencao.csv`
   - `veiculos_locados.csv`
   - `veiculos_cedidos.csv`
   *Nota: Todos esses arquivos utilizam o caractere especial `¬` como separador de colunas.*

5. **Executar o Dashboard Streamlit:**
   Execute o comando abaixo para iniciar o servidor web de desenvolvimento local:
   ```bash
   python -m streamlit run src/app.py
   ```
   
   Após a inicialização, o Streamlit abrirá automaticamente uma janela em seu navegador padrão no endereço `http://localhost:8501`.

6. **Validação Rápida de Script:**
   Caso queira testar apenas o carregamento do pipeline de dados e a geração dos novos campos de anomalia no terminal (sem subir o servidor Streamlit), você pode rodar a validação básica usando:
   ```bash
   python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('src').resolve())); from app import load_all_data; _, df, _, _, _, _, _, _ = load_all_data(); print('Registros carregados:', len(df)); print('Colunas de outliers calculadas com sucesso!')"
   ```

---
