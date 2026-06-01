# src/config.py

# ── Recorte temporal ───────────────────────────────────────────
ANO        = 2025
MES_INICIO = 202501
MES_FIM    = 202512

# ── Arquivos de entrada ────────────────────────────────────────
from pathlib import Path
DATA_DIR = Path('dados')
ARQUIVOS = {
    'veiculos'    : f'{DATA_DIR}/veiculos.csv',
    'manutencoes' : f'{DATA_DIR}/veiculos_manutencao.csv',
    'locados'     : f'{DATA_DIR}/veiculos_locados.csv',
    'cedidos'     : f'{DATA_DIR}/veiculos_cedidos.csv',
}
SEP_CSV   = '¬'
DTYPE_BASE = {'cd_municipio': str, 'cd_renavam_vm': str}

# ── Limiares da quarentena ─────────────────────────────────────
TOLERANCIA_FLOAT    = 0.01
LIMIAR_INVESTIGACAO = 10_000
LIMIAR_QUARENTENA   = 100_000

# ── Limiares de anomalia ───────────────────────────────────────
LIMIAR_ZSCORE          = 3.0
LIMIAR_IQR_MULTIPLIER  = 1.5
IF_CONTAMINATION       = 0.05

TIPO_VINCULACAO = {'p': 'Próprio', 'l': 'Locado', 'c': 'Cedido'}

SITUACAO_VEICULO = {
    1: 'Em uso',    2: 'Cedido para Terceiros', 3: 'Ocioso',
    4: 'Sucata',    5: 'Alienado',              6: 'Devolvido ao Locador',
    7: 'Devolvido ao Cedente'
}

PRIORIDADE_MODO_CONTRATO = {
    'Aditivo de Prazo e Acréscimo': 5, 'Aditivo de Acréscimo': 4,
    'Aditivo de Renovação': 3,         'Aditivo de Prazo': 2,
    'Aditivo de Redução': 1,           'Contrato Original': 0
}
FINALIDADES_SUSPEITAS = [
    'Pátio (veículos inservíveis ou irrecuperáveis – sucata)',
    'Garagem (veículos ociosos)'
]