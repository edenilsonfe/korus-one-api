"""AMIOFE-E item catalog — Felício et al. 2010 protocol (expanded scores)."""

from __future__ import annotations

# (id_suffix, text, max_points hint for validation)
FACE_ITEMS = [
    ("simetria", "Simetria facial", 4),
    ("proporcao_tercos", "Proporção entre os terços da face", 4),
    ("sulco_nasolabial", "Sulco nasolabial", 4),
]

BOCHECHAS_ITEMS = [
    ("volume", "Volume das bochechas", 4),
    ("tensao_configuracao", "Tensão/configuração das bochechas", 4),
]

RELACAO_MANDIBULAR_ITEMS = [
    ("relacao_vertical", "Relação vertical mandíbula/maxila (EFL)", 4),
    ("relacao_anteroposterior", "Relação antero-posterior", 4),
    ("linha_media", "Relação com a linha média", 4),
]

LABIOS_ITEMS = [
    ("funcao_repouso", "Função labial no repouso", 4),
    ("volume_configuracao", "Volume e configuração labial", 4),
    ("comissuras", "Comissuras labiais", 4),
]

MENTUAL_ITEMS = [
    ("contracao", "Contração do músculo mentual (lábios ocluídos)", 4),
]

LINGUA_ITEMS = [
    (
        "posicao_aparencia",
        "Posição/aparência da língua (contida, apertamento, interposição)",
        4,
    ),
    ("volume", "Volume/aparência da língua", 4),
]

PALATO_ITEMS = [
    ("largura", "Largura do palato duro", 4),
    ("altura", "Altura do palato duro", 4),
]

MOB_LINGUA_ITEMS = [
    ("protrusao", "Mobilidade da língua — protrusão", 6),
    ("retracao", "Mobilidade da língua — retração", 6),
    ("lateral_d", "Mobilidade da língua — lateral direita", 6),
    ("lateral_e", "Mobilidade da língua — lateral esquerda", 6),
    ("elevar", "Mobilidade da língua — elevar", 6),
    ("abaixar", "Mobilidade da língua — abaixar", 6),
]

MOB_LABIAL_ITEMS = [
    ("protrusao", "Mobilidade labial — protrusão", 6),
    ("retracao", "Mobilidade labial — retração", 6),
    ("lateral_d", "Mobilidade labial — lateral direita", 6),
    ("lateral_e", "Mobilidade labial — lateral esquerda", 6),
]

MOB_MANDIBULA_ITEMS = [
    ("abaixar", "Mobilidade mandibular — abaixar", 6),
    ("elevar", "Mobilidade mandibular — elevar", 6),
    ("lateral_d", "Mobilidade mandibular — lateral direita", 6),
    ("lateral_e", "Mobilidade mandibular — lateral esquerda", 6),
    ("protruir", "Mobilidade mandibular — protruir", 6),
]

MOB_BOCHECHAS_ITEMS = [
    ("inflar", "Mobilidade das bochechas — inflar", 6),
    ("sugar", "Mobilidade das bochechas — sugar", 6),
    ("retrair", "Mobilidade das bochechas — retrair", 6),
    ("lateralizar_ar", "Mobilidade das bochechas — lateralizar o ar (D/E)", 6),
]

RESPIRACAO_ITEMS = [
    ("modo", "Modo respiratório", 4),
]

DEGLUTICAO_LABIOS_ITEMS = [
    ("comportamento_labios", "Deglutição — comportamento dos lábios", 6),
]

DEGLUTICAO_LINGUA_ITEMS = [
    ("comportamento_lingua", "Deglutição — comportamento da língua", 4),
]

DEGLUTICAO_SINAIS_ITEMS = [
    ("mov_cabeca_corpo", "Movimentação da cabeça ou outras partes do corpo", 2),
    ("deslize_mandibula", "Deslize da mandíbula", 2),
    ("tensao_facial", "Tensão da musculatura facial", 2),
    ("escape_alimento", "Escape de alimento", 2),
    ("engasgo", "Engasgo", 2),
    ("ruido", "Ruído", 2),
]

DEGLUTICAO_EFICIENCIA_ITEMS = [
    ("bolo_solido", "Deglutição — eficiência bolo sólido", 3),
    ("bolo_liquido", "Deglutição — eficiência bolo líquido", 3),
]

MASTIGACAO_PADRAO_ITEMS = [
    ("padrao", "Padrão de mastigação (bilateral/alternada/unilateral/anterior)", 10),
]

MASTIGACAO_SINAIS_ITEMS = [
    ("mov_cabeca_corpo", "Movimentação da cabeça ou outras partes do corpo", 2),
    ("postura_alterada", "Postura alterada", 2),
    ("escape_alimento", "Escape de alimento", 2),
]

MASTIGACAO_MORDIDA_ITEMS = [
    ("mordida", "Mastigação — padrão de mordida (incisivos a molares)", 4),
]

IDENTIFICACAO_ITEMS = [
    ("queixa", "Queixa principal"),
    ("inicio_problema", "Início do problema"),
]

ANALISE_OCLUSAL_ITEMS = [
    ("angle_direito", "Classificação de Angle — lado direito"),
    ("angle_esquerdo", "Classificação de Angle — lado esquerdo"),
    ("linha_media", "Linha média dentária"),
    ("movimentos_funcionais", "Movimentos mandibulares funcionais (medidas e desvios)"),
    ("ruido_atm", "Ruído ATM"),
    ("tercos_face", "Terços da face (cm)"),
]
