"""ABLLS-R domain metadata and manual task overrides (Partington 2006, pt-BR)."""

from __future__ import annotations

# Official domain order (25 areas, letter O unused).
DOMAIN_ORDER: list[str] = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
]

DOMAIN_TITLES: dict[str, str] = {
    "A": "Cooperação e eficácia do reforçador",
    "B": "Desempenho visual",
    "C": "Linguagem receptiva",
    "D": "Imitação motora",
    "E": "Imitação vocal",
    "F": "Pedidos (mands)",
    "G": "Nomeação (tacts)",
    "H": "Intraverbais",
    "I": "Vocalizações espontâneas",
    "J": "Sintaxe e gramática",
    "K": "Brincadeira e lazer",
    "L": "Interação social",
    "M": "Instrução em grupo",
    "N": "Rotinas de sala de aula",
    "P": "Generalização",
    "Q": "Leitura",
    "R": "Matemática",
    "S": "Escrita",
    "T": "Soletração",
    "U": "Vestir-se",
    "V": "Alimentação",
    "W": "Higiene pessoal",
    "X": "Banheiro",
    "Y": "Motor grosso",
    "Z": "Motor fino",
}

# Expected task counts per domain (official ABLLS-R Revised, 544 total).
DOMAIN_TASK_COUNTS: dict[str, int] = {
    "A": 19,
    "B": 27,
    "C": 57,
    "D": 27,
    "E": 20,
    "F": 29,
    "G": 47,
    "H": 49,
    "I": 9,
    "J": 20,
    "K": 15,
    "L": 34,
    "M": 12,
    "N": 10,
    "P": 6,
    "Q": 17,
    "R": 29,
    "S": 10,
    "T": 7,
    "U": 15,
    "V": 10,
    "W": 7,
    "X": 10,
    "Y": 30,
    "Z": 28,
}

# Missing from translated PDF — sourced from official protocol (EN → pt-BR).
MANUAL_ITEMS: dict[str, dict[str, str]] = {
    "M11": {
        "task_name": "Esperar a vez durante a instrução",
        "objective": (
            "Quando participa de instrução em grupo, o aluno esperará sua vez antes de "
            "responder ou realizar a atividade solicitada."
        ),
        "question": "Espera a vez durante atividades de instrução em grupo?",
        "example": (
            "Em uma rodada de perguntas, aguarda que o colega termine antes de levantar "
            "a mão ou responder."
        ),
        "criteria": (
            "2= Espera a vez de forma independente em pelo menos 80% das oportunidades\n"
            "1= Precisa de lembrete verbal em algumas oportunidades"
        ),
        "notes": "Tarefa oficial M11 (ausente no PDF traduzido).",
    },
    "M12": {
        "task_name": "Aprender habilidades novas no formato de ensino em grupo",
        "objective": (
            "O aluno adquirirá habilidades novas quando a instrução é apresentada em "
            "formato de ensino em grupo (não apenas individual)."
        ),
        "question": "Aprende habilidades novas quando ensinadas em grupo?",
        "example": (
            "Aprende a imitar ações ou responder a instruções receptivas apresentadas "
            "a toda a turma."
        ),
        "criteria": (
            "2= Adquire pelo menos uma habilidade nova em contexto de grupo\n"
            "1= Adquire habilidades novas apenas com ensino individual"
        ),
        "notes": "Tarefa oficial M12 (ausente no PDF traduzido).",
    },
}

# Non-official item in PDF translation — drop on build.
SKIP_TASK_IDS: set[str] = set()  # filled at runtime: J20 if adjective task detected

SKIP_TASK_NAME_MARKERS: tuple[str, ...] = (
    "gênero e o número dos adjetivos",
    "genero e o numero dos adjetivos",
)
