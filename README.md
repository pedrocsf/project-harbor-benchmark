<div align="center">

<img src="packaging/linux/llm-evaluator.png" alt="Project Harbor Benchmark logo" width="128" height="128" />

# Project Harbor Benchmark

### A desktop benchmark for LLMs, scored against a fixed question set.

**Load a dataset. Point it at your model. Get comparable scores, and see exactly how each one is computed.**

[![Python](https://img.shields.io/badge/Python-3.14-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/Qt-PySide6-41cd52?style=flat-square&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![ONNX](https://img.shields.io/badge/ONNX-fastembed-005ced?style=flat-square&logo=onnx&logoColor=white)](https://github.com/qdrant/fastembed)
[![Metrics](https://img.shields.io/badge/metrics-11-e8335d?style=flat-square)](#metrics)
[![PyInstaller](https://img.shields.io/badge/packaged_with-PyInstaller-2c3e50?style=flat-square)](https://pyinstaller.org/)
[![Platforms](https://img.shields.io/badge/platform-Linux_%7C_Windows-0f172a?style=flat-square)](#quick-start)
[![MIT license](https://img.shields.io/badge/license-MIT-f4c430?style=flat-square)](LICENSE)

[Features](#features) · [Quick start](#quick-start) · [Usage](#usage) · [Metrics](#metrics) · [Architecture](#architecture) · [How scoring works](#how-scoring-works) · [Repository layout](#repository-layout) · [Contributing](#contributing) · [License](#license)

</div>

<br />

<div align="center">
<img src="docs/assets/main-window.png" alt="Project Harbor Benchmark in demo mode, showing the dataset sidebar, the metrics panel and the per-question score table" width="900" />
</div>

<br />

Project Harbor Benchmark lets a team evaluate different LLM approaches on the same dataset in the same way. For each question, the app calls your model through an OpenAI-compatible endpoint (for example `http://127.0.0.1:1234/v1/chat/completions`), or through the native Anthropic or Gemini API, compares the answer with the expected one, and scores it from 0 to 1 with any of eleven metrics. Scoring is offline: the embedding model ships inside the app and every metric runs on your machine, except the LLM judge, which asks a model for each rating. Only calls to a cloud provider need a connection and an API key.

## Features

- **Eleven metrics, all configurable.** Embedding similarity, Exact match, Token F1, Token recall, Contains answer, ROUGE-1, ROUGE-2, ROUGE-L, BLEU, chrF++ and an LLM judge. Each one has its own parameters, and switching metric or parameters after a run re-scores the stored answers without calling the LLM again.
- **Info window.** Formulas, parameters with defaults and ranges, and the reference papers for every metric.
- **"How it works" explorer (demo mode).** One animated scene per metric that shows, step by step, how two answers become a score.
- **Offline scoring.** The embedding model is bundled and the dataset is a plain JSON file you choose. Only the LLM judge and cloud providers need a connection.
- **Overview chart.** One PNG with every metric at once: a bar for the mean and a dot for the median.
- **Run statistics.** Median, highest and lowest score, response times, empty answers and average answer length.
- **JSON and CSV export** of every run, including the parameters used.
- **Demo mode** that computes real scores with the real metrics on 12 sample questions, with no LLM and no dataset needed.
- **Native desktop app** for Linux (`.AppImage`) and Windows, built with Qt.

## Quick start

Download the latest build from the releases page (or from the `build` workflow artifacts), or run it from source.

### Demo mode

The fastest way to see the app. It opens the same window with 12 sample questions and a simulated run, makes no network calls, and needs no embedding model download:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python main_demo.py
```

The scores are real: every metric runs its real code on the sample answers. The embedding similarity uses precomputed vectors from [`demo/demo_embeddings.json`](demo/demo_embeddings.json), and the LLM judge uses fixed sample ratings, requantized to the rating scale you pick. The sample answers themselves are fictional and must not be mistaken for results of a real model. Export and Export chart write real files. The data lives in [`demo/demo_data.py`](demo/demo_data.py).

### Real mode

```sh
.venv/bin/python scripts/prefetch_model.py
.venv/bin/python main.py
```

`prefetch_model.py` downloads the embedding model (about 240 MB) into `models/`, which is what lets the app run offline afterwards. Then you need a dataset (see [Dataset format](#dataset-format)) and an LLM endpoint (see [Supported providers](#supported-providers)).

### Building the AppImages

```sh
APPIMAGE_EXTRACT_AND_RUN=1 APPIMAGETOOL=<path to appimagetool> sh scripts/build_appimage.sh normal
APPIMAGE_EXTRACT_AND_RUN=1 APPIMAGETOOL=<path to appimagetool> sh scripts/build_appimage.sh demo
```

`normal` builds the real app and `demo` builds the demo app.

### Tests

```sh
.venv/bin/python -m pytest
```

In a headless environment, set `QT_QPA_PLATFORM=offscreen` first.

## Usage

1. Open the app. A splash screen shows while the embedding model loads.
2. Click **Load dataset…** and pick your JSON file. Everything else stays disabled until a valid dataset is loaded.
3. Enter the LLM URL. **API key** and **Model** are optional for local servers, and the URL works without `http://`. The provider is picked from the URL.
4. Choose a **Metric** (default: Embedding similarity) and, if you want, adjust it with **Parameters…**.
5. Click **Run benchmark** and follow the progress. The table and the metrics panel fill in when it finishes.
6. Use **Export…** to save the result as JSON or CSV, and **Export chart…** to save the overview PNG.

Loading a new dataset clears the previous result. Changing the metric or its parameters after a run recalculates the score column immediately from the answers already collected.

| Area | What it does |
|---|---|
| **Dataset** | **Load dataset…** opens a JSON file; the name and question count appear below. |
| **Model endpoint** | URL, optional API key and optional model name. The provider is chosen from the URL. |
| **Metric** | Drop-down with the eleven metrics. Changing it re-scores the last run without calling the model. |
| **Parameters…** | Opens a dialog with the selected metric's parameters. See [Metric parameters](#metric-parameters). |
| **Run benchmark / Stop run** | Starts the run, or cancels it (closing the window mid-run is safe). |
| **Metrics panel** | Average, median, highest and lowest score, response times, empty answers and average answer length. Binary metrics show correct and incorrect counts instead. |
| **Score table** | One row per question: expected answer, LLM answer and a score bar. |
| **How it works** | Demo only. Opens the animated metric explorer. |
| **Info** | Formulas, parameters and references for every metric. |
| **Export…** / **Export chart…** | JSON or CSV of the run, and the overview PNG. |

### Dataset format

The dataset is a JSON list of questions. See [`examples/questions.example.json`](examples/questions.example.json).

```json
[
  {
    "id": "1",
    "question": "What is the capital of Brazil?",
    "expected_answer": "The capital of Brazil is Brasília."
  }
]
```

`id` is optional; when missing, the position in the list is used. The dataset is never bundled with the app, so your team can share and version it separately.

### Metric parameters

<div align="center">
<img src="docs/assets/parameters-dialog.png" alt="The Parameters dialog for Token F1" width="360" />
</div>

<br />

**Parameters…** opens a dialog for the selected metric only, with one control per parameter, a description under each, and **Restore defaults**. Pressing **Apply** re-scores the last run immediately, without calling the model. The defaults reproduce the classic definition of each metric, and the sidebar says when the defaults are in use. Values live in memory for the session and reset when the app closes. The JSON export includes them under `method_parameters`, so a result always says how it was scored.

For the LLM judge, **Set temperature** is off by default, which means the provider's own default is used (some models reject custom temperatures). The **Temperature** value only applies when it is on.

### Animations

The interface uses short animations (window and page fades, staggered metric cards, growing score bars, smooth progress). Set `HARBOR_REDUCE_MOTION=1` before starting the app to turn them all off, including the ones in the explorer.

### The "How it works" explorer

<div align="center">
<img src="docs/assets/how-it-works.png" alt="The How it works window on BLEU at its last step" width="900" />
</div>

<br />

In demo mode, **How it works** opens a window with one animated scene per metric. Pick a metric on the left and an example on the top right; the scene plays through numbered steps (for BLEU: precision per n-gram order, geometric mean, brevity penalty, final score) while the matching line of the formula is highlighted and the numbers are filled in. The scene follows the current **Parameters…** values, so changing the BLEU smoothing or the F1 beta changes what you see. Playback can be paused, restarted and stepped, at 0.5×, 1× or 2× speed.

## Supported providers

The provider is chosen from the **URL**; there is no extra field.

| Provider | URL | API key | Model |
|----------|-----|---------|-------|
| OpenAI-compatible (OpenAI, LM Studio, Ollama, vLLM, OpenRouter, Groq…) | The full `…/chat/completions` URL | Optional (`Authorization: Bearer`) | Optional |
| Anthropic | `https://api.anthropic.com` (the path `/v1/messages` is added when missing) | Required (`x-api-key`) | Required, for example `claude-sonnet-4-5` |
| Google Gemini | `https://generativelanguage.googleapis.com` (the path `/v1beta/models/<model>:generateContent` is built from **Model**), or the full `…:generateContent` URL | Required (`x-goog-api-key`) | Required when the URL has no path |

Any URL containing `/chat/completions` is treated as OpenAI-compatible, including the compatibility endpoints of Anthropic and Google. Anthropic answers are capped at 4096 output tokens.

## Metrics

Every metric compares the LLM answer with `expected_answer` and returns a score from 0 to 1 per question. The **Parameters** column lists what you can configure in **Parameters…**, with defaults in bold.

| Metric | Per-question score | Parameters (defaults in bold) |
|---|---|---|
| Embedding similarity | Similarity between the two embeddings, scaled to 0 to 1. Captures meaning and tolerates paraphrase; multilingual model bundled. | Similarity function (**cosine**, dot product, angular, euclidean, manhattan); Negative values (**clip**, rescale); Normalize vectors (**on**) |
| Exact match | 0 or 1 after normalization | Lowercase (**on**); Strip accents (off); Remove punctuation (**on**); Remove articles (**English**, Portuguese, both, none) |
| Token F1 | F-measure over normalized tokens, counting repeats | The four normalization options above; Beta (**1.0**, range 0.1 to 10) |
| Token recall | Share of expected tokens found in the answer. Does not penalize extra words, so it suits verbose models. | The four normalization options above |
| Contains answer | 0 or 1: the normalized expected answer appears in the answer | The four normalization options above; Match mode (**whole words**, substring) |
| ROUGE-1, ROUGE-2 | Unigram or bigram overlap | Score type (**F-measure**, precision, recall); Beta (**1.0**); Lowercase (**on**) |
| ROUGE-L | Longest common subsequence | Same as ROUGE-1 |
| BLEU | Sentence BLEU (`sacrebleu`); the panel also shows corpus BLEU | Maximum n-gram order (**4**, 1 to 6); Smoothing method (**exp**, floor, add-k, none); Floor value (**0.1**); Add-k value (**1**); Tokenizer (**13a**, intl, char, none); Ignore letter case (off); Effective order (**on**) |
| chrF++ | Character n-gram F-score (`sacrebleu`). Tolerates inflection and accents better than word metrics. | Character n-gram order (**6**, 1 to 10); Word n-gram order (**2**, 0 to 3); Recall weight beta (**2**, 1 to 6); Ignore letter case (off); Include whitespace (off); Epsilon smoothing (off) |
| LLM judge | Rating given by a model, divided by the scale maximum | Rating scale maximum (**10**, 2 to 100); Prompt template; Samples per answer (**1**, 1 to 10, averaged); Set temperature (**off**); Temperature (**0.0**, 0 to 2, only when set) |

The LLM judge uses the same endpoint, API key and model as the run, one extra call per sample. It needs a connection and is left out of the overview chart unless the run used it. Binary metrics (Exact match, Contains answer) show correct and incorrect counts instead of median, highest and lowest score.

Things to keep in mind when reading the scores:

- Exact match and F1 are designed for short answers. Chat models tend to answer in full sentences, which lowers these scores even when the answer is right. Either write the expected answers in the same style or configure the LLM to answer briefly.
- The ROUGE tokenizer accepts accented letters, unlike the original `rouge-score`, which only considers `a-z` and `0-9`. Results on non-English text can therefore differ from it.
- Sentence BLEU is unstable on very short answers. Corpus BLEU is more reliable for comparing approaches.
- Applying a benchmark's formula to your own dataset does not reproduce that benchmark's published score; it only reuses the calculation.

### Info window

**Info** lists every metric with its formula, its parameters (default and range) and the papers it comes from, so a score can be explained to someone who did not run the app.

### Overview chart

<div align="center">
<img src="docs/assets/overview.png" alt="Metric overview chart exported by Project Harbor Benchmark" width="600" />
</div>

<br />

**Export chart…** renders a PNG in which every row is a metric: its name, a bar for the mean and a dot for the median. Reading down the chart shows which metrics are generous and which are strict on the same run. The chart is drawn with Qt itself, so it needs no plotting library, and it is only available after a run.

### References

| Metric | Papers |
|---|---|
| Embedding similarity | Reimers & Gurevych 2019, [Sentence-BERT](https://aclanthology.org/D19-1410/), EMNLP-IJCNLP; Steck, Ekanadham & Kallus 2024, [Is Cosine-Similarity of Embeddings Really About Similarity?](https://arxiv.org/abs/2403.05440), WWW '24 Companion |
| Exact match | Chen, Stanovsky, Singh & Gardner 2019, [Evaluating Question Answering Evaluation](https://aclanthology.org/D19-5817/), MRQA@EMNLP; Bulian et al. 2022, [Tomayto, Tomahto. Beyond Token-level Answer Equivalence for Question Answering Evaluation](https://aclanthology.org/2022.emnlp-main.20/), EMNLP |
| Token F1 | Christen, Hand & Kirielle 2024, [A Review of the F-Measure: Its History, Properties, Criticism, and Alternatives](https://doi.org/10.1145/3606367), ACM Computing Surveys 56(3); Chen et al. 2019 (above) |
| Token recall | Adlakha et al. 2024, [Evaluating Correctness and Faithfulness of Instruction-Following Models for Question Answering](https://aclanthology.org/2024.tacl-1.38/), TACL 12 |
| Contains answer | Adlakha et al. 2024 (section 4.1, "Recall (Strict)"); Kamalloo, Dziri, Clarke & Rafiei 2023, [Evaluating Open-Domain Question Answering in the Era of Large Language Models](https://aclanthology.org/2023.acl-long.307/), ACL |
| ROUGE-1 / ROUGE-2 | Lin 2004, [ROUGE: A Package for Automatic Evaluation of Summaries](https://aclanthology.org/W04-1013/), Text Summarization Branches Out; Grusky 2023, [Rogue Scores](https://aclanthology.org/2023.acl-long.107/), ACL |
| ROUGE-L | Lin & Och 2004, [Automatic Evaluation of Machine Translation Quality Using Longest Common Subsequence and Skip-Bigram Statistics](https://aclanthology.org/P04-1077/), ACL; Lin 2004 (above) |
| BLEU | Papineni et al. 2002, [BLEU: a Method for Automatic Evaluation of Machine Translation](https://aclanthology.org/P02-1040/), ACL; Chen & Cherry 2014, [A Systematic Comparison of Smoothing Techniques for Sentence-Level BLEU](https://aclanthology.org/W14-3346/), WMT; Post 2018, [A Call for Clarity in Reporting BLEU Scores](https://aclanthology.org/W18-6319/), WMT; Callison-Burch, Osborne & Koehn 2006, [Re-evaluating the Role of Bleu in Machine Translation Research](https://aclanthology.org/E06-1032/), EACL |
| chrF++ | Popović 2015, [chrF: character n-gram F-score for automatic MT evaluation](https://aclanthology.org/W15-3049/), WMT; Popović 2016, [chrF deconstructed: beta parameters and n-gram weights](https://aclanthology.org/W16-2341/), WMT; Popović 2017, [chrF++: words helping character n-grams](https://aclanthology.org/W17-4770/), WMT |
| LLM judge | Zheng et al. 2023, [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685), NeurIPS Datasets and Benchmarks; Gu et al. 2024, [A Survey on LLM-as-a-Judge](https://arxiv.org/abs/2411.15594) |

## Architecture

Project Harbor Benchmark follows Clean Architecture with an MVC presentation layer. Dependencies point inward: `presentation → domain ← data`.

```
┌──────────────────────────────── presentation ─────────────────────────────────┐
│  views         main window, metrics panel, parameters dialog, info window,    │
│                overview chart, metric explorer (animated scenes)              │
│  controllers   evaluation, startup and metric explorer (background threads)   │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ calls use cases
┌──────────────────────────────────────▼────────────────────────────────────────┐
│                                   domain                                      │
│  entities       Question, EvaluationResult, MetricOverview                    │
│  use cases      RunEvaluation, LoadQuestions, RescoreResult, ExportResult,    │
│                 BuildMetricOverview, BuildMetricWalkthrough, ...              │
│  interfaces     LanguageModelGateway, QuestionRepository, ResultRepository,   │
│                 TextEncoder                                                   │
│  scoring        ScoringMethod + parameter_specs; pure-Python metrics          │
└──────────────────────────────────────▲────────────────────────────────────────┘
                                       │ implements interfaces
┌──────────────────────────────────────┴────────────────────────────────────────┐
│                                    data                                       │
│  gateways       OpenAI-compatible, Anthropic, Gemini (routed by URL)          │
│  repositories   JSON dataset reader, JSON/CSV result exporter                 │
│  scoring        BLEU and chrF++ (sacrebleu), fastembed text encoder           │
└───────────────────────────────────────────────────────────────────────────────┘

Scoring pipeline:
  expected + given answer → normalize → ScoringMethod.score() → 0..1 per question
  → mean / median / min / max → metrics panel, overview chart, JSON/CSV export
```

- **Use cases** each expose a single action, for example `RunEvaluation`, `RescoreResult` and `BuildMetricOverview`.
- **Scoring** goes through the `ScoringMethod` interface (`identifier`, `display_name`, `score_kind`, `parameter_specs`, `parameters`, `score()`, `prepare()` and an optional `corpus_score()`), so adding a metric means adding one class and registering it.
- **Controllers** are thin: they run use cases on background threads and hand results to the views. `EvaluationController.shutdown()` cancels and joins the worker on exit.
- **Views** only display data and forward user actions. Colors live in `presentation/views/branding.py` and the Qt stylesheet in `presentation/views/theme.py`.

## How scoring works

1. **Call.** For each question the gateway for the chosen provider sends the prompt and returns the answer, with its response time. Empty answers are counted.
2. **Normalize.** The token metrics lowercase, optionally strip accents, remove punctuation and remove articles (English by default), according to the metric's parameters. BLEU and chrF++ tokenize through `sacrebleu`.
3. **Compare.** Each metric computes its per-question score in the 0 to 1 range: a cosine (or other) similarity between embeddings, a token or n-gram overlap, a longest common subsequence, a character n-gram F-score, or a rating divided by its scale. The LLM judge is the only metric that makes extra model calls.
4. **Aggregate.** The metrics panel shows mean, median, highest and lowest score. BLEU also shows corpus BLEU, which pools all questions.
5. **Re-score.** Changing the metric or its parameters re-scores the stored answers locally through `RescoreResult`, without calling the model again. The exception is the LLM judge, which needs new calls.
6. **Export.** The JSON export includes the metric and its `method_parameters`; the overview chart scores the same answers with every metric.

## Repository layout

```
domain/              entities, repository and gateway interfaces, use cases,
                     explanations (metric walkthroughs), pure-Python scoring methods
data/                dataset reader, result exporter, OpenAI-compatible, Anthropic and
                     Gemini gateways, BLEU and chrF++, fastembed text encoder
presentation/
  controllers/       evaluation, startup and metric explorer controllers
  views/             splash, main window, metrics panel, parameters dialog, info window,
                     overview chart, metric_explorer/ (animated scenes), theme
demo/                sample data, precomputed embeddings and demo components for main_demo.py
examples/            sample dataset
scripts/             model prefetch and AppImage build
packaging/linux/     AppRun, .desktop entry and icon
docs/assets/         screenshots used in this README
tests/
```

## Contributing

Issues and pull requests are welcome. Please run `python -m pytest` before opening a pull request, and keep each change focused on a single behavior.

## License

Released under the [MIT License](LICENSE).
