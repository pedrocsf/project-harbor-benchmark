from dataclasses import dataclass

from domain.entities.retrieved_context import RetrievedContext

DEMO_RAG_ENDPOINT = "http://127.0.0.1:8000/rag"
DEMO_RUN_NAME = "demo-run.jsonl"


@dataclass(frozen=True)
class DemoRagEntry:
    contexts: tuple[RetrievedContext, ...]
    relevant_context_ids: tuple[str, ...]
    relevant_passages: tuple[str, ...]
    statements: tuple[str, ...]
    verdicts: tuple[bool, ...]
    context_relevance: tuple[float, ...]
    generated_questions: tuple[str, ...]


def _context(identifier: str, text: str, score: float) -> RetrievedContext:
    return RetrievedContext(identifier, text, score)


DEMO_RAG_ENTRIES = {
    "1": DemoRagEntry(
        contexts=(
            _context("geo-fr#1", "Paris é a capital e a cidade mais populosa da França.", 0.91),
            _context("geo-fr#4", "Lyon é a terceira maior cidade da França.", 0.74),
            _context("tur-eu#2", "A Torre Eiffel fica em Paris e foi inaugurada em 1889.", 0.70),
        ),
        relevant_context_ids=("geo-fr#1",),
        relevant_passages=(),
        statements=("A capital da França é Paris.",),
        verdicts=(True,),
        context_relevance=(1.0, 0.0, 0.0),
        generated_questions=(
            "Qual é a capital da França?",
            "Que cidade é a capital francesa?",
            "Paris é a capital de qual país?",
        ),
    ),
    "2": DemoRagEntry(
        contexts=(
            _context("astro#3", "O Sistema Solar tem oito planetas desde que Plutão foi reclassificado em 2006.", 0.88),
            _context("astro#7", "Plutão passou a ser classificado como planeta anão pela União Astronômica Internacional.", 0.80),
            _context("astro#9", "Júpiter é o maior planeta do Sistema Solar.", 0.77),
        ),
        relevant_context_ids=("astro#3", "astro#7"),
        relevant_passages=(),
        statements=("Existem oito planetas no Sistema Solar.",),
        verdicts=(True,),
        context_relevance=(1.0, 1.0, 0.0),
        generated_questions=(
            "Quantos planetas existem no Sistema Solar?",
            "Quantos planetas tem o Sistema Solar?",
            "Qual é o número de planetas do Sistema Solar?",
        ),
    ),
    "3": DemoRagEntry(
        contexts=(
            _context("lit#12", "Dom Casmurro é um romance de Machado de Assis publicado em 1899.", 0.86),
            _context("lit#5", "Machado de Assis fundou a Academia Brasileira de Letras em 1897.", 0.79),
            _context("lit#2", "Memórias Póstumas de Brás Cubas foi publicado em 1881.", 0.66),
        ),
        relevant_context_ids=(),
        relevant_passages=("Dom Casmurro é um romance de Machado de Assis publicado em 1899.",),
        statements=("Machado de Assis escreveu Dom Casmurro.",),
        verdicts=(True,),
        context_relevance=(1.0, 0.0, 0.0),
        generated_questions=(
            "Quem escreveu Dom Casmurro?",
            "Qual é o autor de Dom Casmurro?",
            "Que livro Machado de Assis escreveu?",
        ),
    ),
    "4": DemoRagEntry(
        contexts=(
            _context("geo-oc#2", "O Atlântico é o segundo maior oceano do planeta.", 0.83),
            _context("geo-oc#1", "O Oceano Pacífico é o maior e mais profundo oceano do mundo.", 0.82),
        ),
        relevant_context_ids=("geo-oc#1",),
        relevant_passages=(),
        statements=("O maior oceano do mundo é o Oceano Pacífico.",),
        verdicts=(True,),
        context_relevance=(0.0, 1.0),
        generated_questions=(
            "Qual é o maior oceano do mundo?",
            "Qual oceano é o maior do planeta?",
            "O Oceano Pacífico é o maior oceano?",
        ),
    ),
    "5": DemoRagEntry(
        contexts=(
            _context("hist#8", "A missão Apollo 13 sofreu uma explosão a caminho da Lua em 1970.", 0.81),
            _context("hist#3", "O programa Apollo foi criado pela NASA em 1961.", 0.78),
            _context("hist#5", "Neil Armstrong pisou na Lua em 20 de julho de 1969, na missão Apollo 11.", 0.76),
        ),
        relevant_context_ids=("hist#5",),
        relevant_passages=(),
        statements=("O homem pisou na Lua pela primeira vez em 1969.", "A primeira missão a pousar na Lua foi a Apollo 11."),
        verdicts=(True, True),
        context_relevance=(0.0, 0.0, 1.0),
        generated_questions=(
            "Em que ano foi a missão Apollo 11?",
            "Quando o homem chegou à Lua?",
            "Qual missão levou o homem à Lua em 1969?",
        ),
    ),
    "6": DemoRagEntry(
        contexts=(
            _context("quim#1", "A molécula de água tem dois átomos de hidrogênio e um de oxigênio: H2O.", 0.93),
        ),
        relevant_context_ids=("quim#1",),
        relevant_passages=(),
        statements=("A fórmula química da água é H2O.",),
        verdicts=(True,),
        context_relevance=(1.0,),
        generated_questions=(
            "Qual é a fórmula química da água?",
            "Como se escreve a água em fórmula química?",
            "H2O é a fórmula de qual substância?",
        ),
    ),
    "7": DemoRagEntry(
        contexts=(
            _context("geom#4", "Um pentágono tem cinco lados.", 0.72),
            _context("geom#9", "Um octógono tem oito lados.", 0.70),
        ),
        relevant_context_ids=("geom#2",),
        relevant_passages=(),
        statements=("Um hexágono tem seis lados.",),
        verdicts=(False,),
        context_relevance=(0.0, 0.0),
        generated_questions=(
            "Quanto é cinco mais um?",
            "Qual número vem depois do cinco?",
            "Como se escreve o número 6 por extenso?",
        ),
    ),
    "8": DemoRagEntry(
        contexts=(
            _context("geo-br#7", "O Amazonas é o rio mais extenso do Brasil e o de maior volume de água do mundo.", 0.89),
            _context("geo-br#3", "O rio São Francisco atravessa cinco estados brasileiros.", 0.75),
        ),
        relevant_context_ids=("geo-br#7",),
        relevant_passages=(),
        statements=("O rio Amazonas é o mais extenso do Brasil.",),
        verdicts=(True,),
        context_relevance=(1.0, 0.0),
        generated_questions=(
            "Qual é o rio mais extenso do Brasil?",
            "Qual é o maior rio brasileiro?",
            "O Amazonas é o rio mais longo do Brasil?",
        ),
    ),
    "9": DemoRagEntry(
        contexts=(
            _context("art#3", "Leonardo da Vinci pintou a Mona Lisa entre 1503 e 1519.", 0.92),
            _context("art#9", "A Mona Lisa está exposta no Museu do Louvre, em Paris.", 0.85),
        ),
        relevant_context_ids=("art#3",),
        relevant_passages=(),
        statements=("A Mona Lisa foi pintada por Michelangelo.",),
        verdicts=(False,),
        context_relevance=(1.0, 0.0),
        generated_questions=(
            "Quem pintou a Mona Lisa?",
            "Qual artista é o autor da Mona Lisa?",
            "A Mona Lisa foi pintada por quem?",
        ),
    ),
    "10": DemoRagEntry(
        contexts=(
            _context("mat#2", "A raiz quadrada de 144 é 12, porque 12 × 12 = 144.", 0.90),
            _context("mat#6", "A raiz quadrada de 169 é 13.", 0.80),
        ),
        relevant_context_ids=("mat#2",),
        relevant_passages=(),
        statements=("A raiz quadrada de 144 é 12.",),
        verdicts=(True,),
        context_relevance=(1.0, 0.0),
        generated_questions=(
            "Quanto é seis mais seis?",
            "Qual número vem depois do onze?",
            "Quantos meses tem um ano?",
        ),
    ),
    "11": DemoRagEntry(
        contexts=(
            _context("ling#1", "O português é a língua oficial e a mais falada do Brasil.", 0.90),
        ),
        relevant_context_ids=("ling#1",),
        relevant_passages=(),
        statements=(),
        verdicts=(),
        context_relevance=(1.0,),
        generated_questions=(),
    ),
    "12": DemoRagEntry(
        contexts=(
            _context("fis#4", "Ao nível do mar, a água pura ferve a 100 graus Celsius.", 0.87),
            _context("fis#9", "Em altitudes elevadas, a água ferve abaixo de 100 °C.", 0.82),
        ),
        relevant_context_ids=(),
        relevant_passages=("A água ferve a 100 graus Celsius ao nível do mar.",),
        statements=("A água ferve a 100 °C ao nível do mar.",),
        verdicts=(True,),
        context_relevance=(1.0, 0.0),
        generated_questions=(
            "A que temperatura a água ferve ao nível do mar?",
            "Qual é o ponto de ebulição da água?",
            "Em quantos graus a água ferve?",
        ),
    ),
}
