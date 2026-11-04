from dataclasses import dataclass


@dataclass(frozen=True)
class PaperReference:
    citation: str
    url: str


@dataclass(frozen=True)
class MetricInfo:
    name: str
    formula: str
    explanation: str
    papers: tuple[PaperReference, ...]


PROJECT_TITLE = "About Project Harbor Benchmark"
PROJECT_DESCRIPTION = (
    "Project Harbor Benchmark lets a team evaluate different LLM approaches on the same dataset, "
    "in the same way. You load a JSON list of questions with their expected answers, point the "
    "app at a model endpoint (OpenAI-compatible, Anthropic or Gemini), and it asks every question, "
    "compares each answer with the expected one and gives it a score from 0 to 1."
)
PROJECT_NOTES = (
    "Scoring runs locally (the embedding model is bundled with the app) for every metric except "
    "the LLM judge, which calls your model endpoint. Cloud providers need a connection. Changing the metric after a run re-scores the stored answers "
    "without calling the model again."
)
METRICS_TITLE = "Metrics and original papers"
METRICS_INTRO = (
    "Each metric below was proposed in the work cited under it. The implementations in this app "
    "follow those definitions; the formulas are shown in a simplified form."
)

METRIC_INFOS = (
    MetricInfo(
        name="Embedding similarity",
        formula="score = max(0, cos(E(expected), E(answer)))",
        explanation=(
            "Both texts are mapped to dense vectors by a multilingual sentence encoder "
            "(paraphrase-multilingual-MiniLM-L12-v2) and compared with cosine similarity, so "
            "answers with the same meaning but different words score high. Negative values are "
            "clipped to 0 and an empty answer scores 0."
        ),
        papers=(
            PaperReference(
                "Reimers & Gurevych (2019). Sentence-BERT: Sentence Embeddings using Siamese "
                "BERT-Networks. EMNLP-IJCNLP 2019.",
                "https://arxiv.org/abs/1908.10084",
            ),
            PaperReference(
                "Reimers & Gurevych (2020). Making Monolingual Sentence Embeddings Multilingual "
                "using Knowledge Distillation. EMNLP 2020.",
                "https://arxiv.org/abs/2004.09813",
            ),
            PaperReference(
                "Wang et al. (2020). MiniLM: Deep Self-Attention Distillation for Task-Agnostic "
                "Compression of Pre-Trained Transformers. NeurIPS 2020.",
                "https://arxiv.org/abs/2002.10957",
            ),
        ),
    ),
    MetricInfo(
        name="Exact match",
        formula="score = 1 if normalize(answer) == normalize(expected) else 0",
        explanation=(
            "The strictest metric: the answer must equal the expected one after lowercasing and "
            "removing punctuation and articles. It is binary (correct or incorrect)."
        ),
        papers=(
            PaperReference(
                "Rajpurkar et al. (2016). SQuAD: 100,000+ Questions for Machine Comprehension of "
                "Text. EMNLP 2016.",
                "https://arxiv.org/abs/1606.05250",
            ),
        ),
    ),
    MetricInfo(
        name="Token F1",
        formula="F1 = 2 · P · R / (P + R),  P = shared / |answer|,  R = shared / |expected|",
        explanation=(
            "Treats both texts as bags of normalized tokens and computes the harmonic mean of "
            "precision and recall of the shared tokens. It rewards partial overlap, unlike "
            "exact match. The token-level F1 for answers comes from SQuAD; the F-measure itself "
            "comes from information retrieval."
        ),
        papers=(
            PaperReference(
                "Rajpurkar et al. (2016). SQuAD: 100,000+ Questions for Machine Comprehension of "
                "Text. EMNLP 2016.",
                "https://arxiv.org/abs/1606.05250",
            ),
            PaperReference(
                "van Rijsbergen (1979). Information Retrieval, 2nd ed. Butterworths (origin of "
                "the F-measure).",
                "https://www.dcs.gla.ac.uk/Keith/Preface.html",
            ),
        ),
    ),
    MetricInfo(
        name="Token recall",
        formula="R = shared / |expected|",
        explanation=(
            "The share of the expected answer's normalized tokens that also appear in the answer. "
            "Unlike Token F1 it does not penalize extra words, so a correct but verbose answer "
            "still scores high. It can be fooled by very long answers that repeat many words."
        ),
        papers=(
            PaperReference(
                "Rajpurkar et al. (2016). SQuAD: 100,000+ Questions for Machine Comprehension of "
                "Text. EMNLP 2016 (answer normalization and token-level overlap).",
                "https://arxiv.org/abs/1606.05250",
            ),
            PaperReference(
                "van Rijsbergen (1979). Information Retrieval, 2nd ed. Butterworths (origin of "
                "precision and recall as used here).",
                "https://www.dcs.gla.ac.uk/Keith/Preface.html",
            ),
        ),
    ),
    MetricInfo(
        name="Contains answer",
        formula="score = 1 if normalize(expected) appears inside normalize(answer) else 0",
        explanation=(
            "Binary check that the expected answer appears, as whole words, anywhere in the "
            "answer. It forgives verbosity but fails when the model answers correctly in other "
            "words. There is no single original paper; this substring accuracy is the usual "
            "way open-domain QA work scores free-form answers from language models."
        ),
        papers=(
            PaperReference(
                "Mallen et al. (2023). When Not to Trust Language Models: Investigating "
                "Effectiveness of Parametric and Non-Parametric Memories. ACL 2023.",
                "https://arxiv.org/abs/2212.10511",
            ),
        ),
    ),
    MetricInfo(
        name="ROUGE-1 and ROUGE-2",
        formula="ROUGE-N = F1 over overlapping n-grams (N = 1 unigrams, N = 2 bigrams)",
        explanation=(
            "Counts the n-grams that the answer and the expected text share and reports the "
            "F-measure of that overlap. ROUGE-1 looks at single words, ROUGE-2 at pairs of "
            "consecutive words, so it is more sensitive to word order."
        ),
        papers=(
            PaperReference(
                "Lin (2004). ROUGE: A Package for Automatic Evaluation of Summaries. ACL Workshop "
                "Text Summarization Branches Out.",
                "https://aclanthology.org/W04-1013/",
            ),
        ),
    ),
    MetricInfo(
        name="ROUGE-L",
        formula="ROUGE-L = F1 with LCS: P = LCS / |answer|,  R = LCS / |expected|",
        explanation=(
            "Uses the longest common subsequence (LCS) between the two texts: words must appear "
            "in the same order but do not need to be adjacent, which captures sentence-level "
            "structure without fixing an n-gram size."
        ),
        papers=(
            PaperReference(
                "Lin (2004). ROUGE: A Package for Automatic Evaluation of Summaries. ACL Workshop "
                "Text Summarization Branches Out.",
                "https://aclanthology.org/W04-1013/",
            ),
        ),
    ),
    MetricInfo(
        name="BLEU",
        formula="BLEU = BP · exp( Σ wₙ · log pₙ ),  n = 1..4,  BP = min(1, e^(1 − r/c))",
        explanation=(
            "Combines the modified n-gram precisions pₙ (from unigrams to 4-grams) with a brevity "
            "penalty BP that punishes answers shorter than the reference. The app uses the "
            "SacreBLEU implementation, which fixes tokenization so scores are comparable, and "
            "also shows a corpus-level BLEU for the whole run."
        ),
        papers=(
            PaperReference(
                "Papineni et al. (2002). BLEU: a Method for Automatic Evaluation of Machine "
                "Translation. ACL 2002.",
                "https://aclanthology.org/P02-1040/",
            ),
            PaperReference(
                "Post (2018). A Call for Clarity in Reporting BLEU Scores. WMT 2018.",
                "https://arxiv.org/abs/1804.08771",
            ),
        ),
    ),
    MetricInfo(
        name="chrF++",
        formula="chrF++ = (1 + β²) · P · R / (β² · P + R),  β = 2,  over character 1-6 grams and word 1-2 grams",
        explanation=(
            "An F-score over character n-grams (plus word unigrams and bigrams in the ++ "
            "variant) that weights recall twice as much as precision. Because it works on "
            "characters, it tolerates plural, conjugation and accent differences better than "
            "word-based metrics, which helps with Portuguese. The app uses the SacreBLEU "
            "implementation."
        ),
        papers=(
            PaperReference(
                "Popović (2015). chrF: character n-gram F-score for automatic MT evaluation. "
                "WMT 2015.",
                "https://aclanthology.org/W15-3049/",
            ),
            PaperReference(
                "Popović (2017). chrF++: words helping character n-grams. WMT 2017.",
                "https://aclanthology.org/W17-4770/",
            ),
            PaperReference(
                "Post (2018). A Call for Clarity in Reporting BLEU Scores. WMT 2018 (SacreBLEU).",
                "https://arxiv.org/abs/1804.08771",
            ),
        ),
    ),
    MetricInfo(
        name="LLM judge",
        formula="score = rating(judge(expected, answer)) / 10,  rating in 0..10",
        explanation=(
            "A language model is asked to grade how correct the answer is compared with the "
            "expected one, ignoring style and length. It is the closest to human judgment for "
            "open answers, but it makes one extra model call per question, needs a connection to "
            "the endpoint you configured (the same one is used as the judge), and inherits the "
            "judge's biases. It is left out of the overview chart unless the run used it."
        ),
        papers=(
            PaperReference(
                "Zheng et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. "
                "NeurIPS 2023.",
                "https://arxiv.org/abs/2306.05685",
            ),
        ),
    ),
)
