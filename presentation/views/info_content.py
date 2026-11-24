from dataclasses import dataclass


@dataclass(frozen=True)
class PaperReference:
    citation: str
    url: str
    coverage: str


@dataclass(frozen=True)
class MetricInfo:
    identifier: str
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
METRICS_TITLE = "Metrics and reference works"
METRICS_INTRO = (
    "The works cited under each metric define or study that metric itself; papers that merely "
    "use it are left out. Every metric is configurable: the defaults reproduce the classic "
    "definition, and the parameters listed in each card can be changed from the main window."
)
PARAMETERS_CAPTION = "Parameters"
PAPERS_CAPTION = "Reference works"

METRIC_INFOS = (
    MetricInfo(
        identifier='embedding',
        name='Embedding similarity',
        formula='score = clip(sim(E(expected), E(answer)))  or  (sim + 1) / 2',
        explanation=(
            'Both texts are encoded by a multilingual sentence encoder and compared with the chosen similarity: cosine, dot product, angular, Euclidean or Manhattan (the last two as 1 / (1 + distance)). Cosine and dot product can be negative, so they are clipped to 0 or rescaled to 0-1. Defaults (cosine, clip) give the classic clipped cosine similarity. An empty answer scores 0.'
        ),
        papers=(
            PaperReference(
                'Reimers & Gurevych (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP-IJCNLP.',
                'https://aclanthology.org/D19-1410/',
                'Defines the sentence embeddings compared with cosine similarity.',
            ),
            PaperReference(
                "Steck, Ekanadham & Kallus (2024). Is Cosine-Similarity of Embeddings Really About Similarity? WWW '24 Companion.",
                'https://arxiv.org/abs/2403.05440',
                'Analyzes when cosine similarity of embeddings is and is not a sound similarity.',
            ),
        ),
    ),
    MetricInfo(
        identifier='exact_match',
        name='Exact match',
        formula='score = 1 if normalize(answer) == normalize(expected) else 0',
        explanation=(
            'Binary: the answer must equal the expected one after the selected normalization (lowercase, strip accents, remove punctuation, drop English and/or Portuguese articles). Each step can be turned off; the defaults reproduce the classic SQuAD-style normalization.'
        ),
        papers=(
            PaperReference(
                'Chen, Stanovsky, Singh & Gardner (2019). Evaluating Question Answering Evaluation. MRQA@EMNLP.',
                'https://aclanthology.org/D19-5817/',
                'Examines exact match as an answer-equivalence measure.',
            ),
            PaperReference(
                'Bulian et al. (2022). Tomayto, Tomahto. Beyond Token-level Answer Equivalence for Question Answering Evaluation. EMNLP.',
                'https://aclanthology.org/2022.emnlp-main.20/',
                'Shows where token-level matching disagrees with answer equivalence.',
            ),
        ),
    ),
    MetricInfo(
        identifier='token_f1',
        name='Token F1',
        formula='F-beta = (1 + β²) · P · R / (β² · P + R),  P = shared / |answer|,  R = shared / |expected|',
        explanation=(
            'Bags of normalized tokens are compared; the F-beta score combines precision and recall of the shared tokens and rewards partial overlap. Normalization steps are options. β = 1 (default) is the classic balanced F1; higher β favors recall.'
        ),
        papers=(
            PaperReference(
                'Christen, Hand & Kirielle (2024). A Review of the F-Measure: Its History, Properties, Criticism, and Alternatives. ACM Computing Surveys 56(3).',
                'https://doi.org/10.1145/3606367',
                'Reviews the F-measure, including its beta weighting.',
            ),
            PaperReference(
                'Chen, Stanovsky, Singh & Gardner (2019). Evaluating Question Answering Evaluation. MRQA@EMNLP.',
                'https://aclanthology.org/D19-5817/',
                'Studies token-level F1 for evaluating question answering.',
            ),
        ),
    ),
    MetricInfo(
        identifier='token_recall',
        name='Token recall',
        formula='R = shared / |expected|',
        explanation=(
            "The share of the expected answer's normalized tokens that also appear in the answer. It does not penalize extra words, so verbose correct answers score high, but very long answers can game it. Normalization steps are options; the defaults match the classic setup."
        ),
        papers=(
            PaperReference(
                'Adlakha et al. (2024). Evaluating Correctness and Faithfulness of Instruction-Following Models for Question Answering. TACL 12.',
                'https://aclanthology.org/2024.tacl-1.38/',
                'Uses token recall to judge correctness of instruction-following models.',
            ),
        ),
    ),
    MetricInfo(
        identifier='contains_answer',
        name='Contains answer',
        formula='score = 1 if normalize(expected) appears in normalize(answer) else 0',
        explanation=(
            'Binary check that the expected answer appears in the answer, either as whole words (default) or as a plain substring. It forgives verbosity but fails when the model answers correctly in other words. Normalization steps are options.'
        ),
        papers=(
            PaperReference(
                'Adlakha et al. (2024). Evaluating Correctness and Faithfulness of Instruction-Following Models for Question Answering. TACL 12.',
                'https://aclanthology.org/2024.tacl-1.38/',
                'Defines the strict recall variant where the answer contains the reference.',
            ),
            PaperReference(
                'Kamalloo, Dziri, Clarke & Rafiei (2023). Evaluating Open-Domain Question Answering in the Era of Large Language Models. ACL.',
                'https://aclanthology.org/2023.acl-long.307/',
                'Studies match-based evaluation of open-domain answers against human judgment.',
            ),
        ),
    ),
    MetricInfo(
        identifier='rouge_1',
        name='ROUGE-1',
        formula='ROUGE-1 = F-beta over overlapping unigrams',
        explanation=(
            'Counts overlapping unigrams between answer and reference and reports precision, recall or the F-measure (F-beta). ROUGE-1 looks at single words. Defaults (F-measure, β = 1, lowercase) give the classic ROUGE F1.'
        ),
        papers=(
            PaperReference(
                'Lin (2004). ROUGE: A Package for Automatic Evaluation of Summaries. Text Summarization Branches Out.',
                'https://aclanthology.org/W04-1013/',
                'Defines the ROUGE family.',
            ),
            PaperReference(
                'Grusky (2023). Rogue Scores. ACL.',
                'https://aclanthology.org/2023.acl-long.107/',
                'Critically examines how ROUGE is implemented and reported.',
            ),
        ),
    ),
    MetricInfo(
        identifier='rouge_2',
        name='ROUGE-2',
        formula='ROUGE-2 = F-beta over overlapping bigrams',
        explanation=(
            'Counts overlapping bigrams between answer and reference and reports precision, recall or the F-measure (F-beta). ROUGE-2 looks at pairs of consecutive words, so it is sensitive to word order. Defaults (F-measure, β = 1, lowercase) give the classic ROUGE F1.'
        ),
        papers=(
            PaperReference(
                'Lin (2004). ROUGE: A Package for Automatic Evaluation of Summaries. Text Summarization Branches Out.',
                'https://aclanthology.org/W04-1013/',
                'Defines the ROUGE family.',
            ),
            PaperReference(
                'Grusky (2023). Rogue Scores. ACL.',
                'https://aclanthology.org/2023.acl-long.107/',
                'Critically examines how ROUGE is implemented and reported.',
            ),
        ),
    ),
    MetricInfo(
        identifier='rouge_l',
        name='ROUGE-L',
        formula='ROUGE-L = F-beta with LCS: P = LCS / |answer|,  R = LCS / |expected|',
        explanation=(
            'Uses the longest common subsequence: words must appear in the same order but need not be adjacent. Reports precision, recall or the F-measure (F-beta). Defaults (F-measure, β = 1, lowercase) give the classic ROUGE-L.'
        ),
        papers=(
            PaperReference(
                'Lin & Och (2004). Automatic Evaluation of Machine Translation Quality Using Longest Common Subsequence and Skip-Bigram Statistics. ACL.',
                'https://aclanthology.org/P04-1077/',
                'Introduces the longest-common-subsequence statistic behind ROUGE-L.',
            ),
            PaperReference(
                'Lin (2004). ROUGE: A Package for Automatic Evaluation of Summaries. Text Summarization Branches Out.',
                'https://aclanthology.org/W04-1013/',
                'Defines the ROUGE family.',
            ),
        ),
    ),
    MetricInfo(
        identifier='bleu',
        name='BLEU',
        formula='BLEU = BP · exp( Σ wₙ · log pₙ ),  n = 1..N,  BP = min(1, e^(1 − r/c))',
        explanation=(
            'Combines modified n-gram precisions up to a maximum order N with a brevity penalty for answers shorter than the reference. Options cover the smoothing method, tokenizer, case and effective order. Defaults (N = 4, exponential smoothing, 13a tokenizer) follow SacreBLEU; a corpus-level BLEU is also shown for the run.'
        ),
        papers=(
            PaperReference(
                'Papineni et al. (2002). BLEU: a Method for Automatic Evaluation of Machine Translation. ACL.',
                'https://aclanthology.org/P02-1040/',
                'Defines BLEU, its n-gram precisions and brevity penalty.',
            ),
            PaperReference(
                'Chen & Cherry (2014). A Systematic Comparison of Smoothing Techniques for Sentence-Level BLEU. WMT.',
                'https://aclanthology.org/W14-3346/',
                'Compares the smoothing methods offered for sentence-level BLEU.',
            ),
            PaperReference(
                'Post (2018). A Call for Clarity in Reporting BLEU Scores. WMT.',
                'https://aclanthology.org/W18-6319/',
                'Explains why tokenization must be fixed, motivating SacreBLEU.',
            ),
            PaperReference(
                'Callison-Burch, Osborne & Koehn (2006). Re-evaluating the Role of Bleu in Machine Translation Research. EACL.',
                'https://aclanthology.org/E06-1032/',
                'Discusses the limits of BLEU as a quality measure.',
            ),
        ),
    ),
    MetricInfo(
        identifier='chrf',
        name='chrF++',
        formula='chrF = (1 + β²) · P · R / (β² · P + R),  over character n-grams up to N and word n-grams up to M',
        explanation=(
            'An F-score over character n-grams (plus word n-grams) that weights recall β times more than precision. It tolerates plural, conjugation and accent differences, which helps with Portuguese. Defaults (character order 6, word order 2, β = 2) give chrF++; word order 0 gives plain chrF.'
        ),
        papers=(
            PaperReference(
                'Popović (2015). chrF: character n-gram F-score for automatic MT evaluation. WMT.',
                'https://aclanthology.org/W15-3049/',
                'Defines the character n-gram F-score.',
            ),
            PaperReference(
                'Popović (2016). chrF deconstructed: beta parameters and n-gram weights. WMT.',
                'https://aclanthology.org/W16-2341/',
                'Studies the beta parameter and n-gram weights.',
            ),
            PaperReference(
                'Popović (2017). chrF++: words helping character n-grams. WMT.',
                'https://aclanthology.org/W17-4770/',
                'Adds word n-grams to chrF, giving chrF++.',
            ),
        ),
    ),
    MetricInfo(
        identifier='llm_judge',
        name='LLM judge',
        formula='score = mean(rating_i) / N,  rating in 0..N,  i = 1..samples',
        explanation=(
            'A language model grades how correct the answer is against the expected one. The rating scale N, the prompt, the number of samples (ratings are averaged) and the temperature are configurable. It costs extra model calls, uses the configured endpoint as judge and inherits its biases. Defaults: N = 10, one sample.'
        ),
        papers=(
            PaperReference(
                'Zheng et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS Datasets and Benchmarks.',
                'https://arxiv.org/abs/2306.05685',
                'Studies LLM judges and their agreement with humans, including biases.',
            ),
            PaperReference(
                'Gu et al. (2024). A Survey on LLM-as-a-Judge.',
                'https://arxiv.org/abs/2411.15594',
                'Surveys how LLM judges are built and assessed.',
            ),
        ),
    ),
)
