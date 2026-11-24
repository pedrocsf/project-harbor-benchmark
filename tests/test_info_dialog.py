import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from main import build_scoring_methods
from presentation.views.info_content import METRIC_INFOS
from presentation.views.info_dialog import InfoDialog


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def scoring_methods():
    return build_scoring_methods(MagicMock())


def dialog_texts(dialog):
    return [label.text() for label in dialog.findChildren(QLabel)]


def test_every_scoring_method_has_metric_info(scoring_methods):
    identifiers = {metric_info.identifier for metric_info in METRIC_INFOS}
    assert {method.identifier for method in scoring_methods} == identifiers


def test_every_metric_cites_papers_with_link_and_coverage():
    for metric_info in METRIC_INFOS:
        assert metric_info.papers
        for paper in metric_info.papers:
            assert paper.url.startswith("https://")
            assert paper.coverage


def test_dialog_shows_every_metric_name(application, scoring_methods):
    texts = set(dialog_texts(InfoDialog(scoring_methods)))
    for metric_info in METRIC_INFOS:
        assert metric_info.name in texts


def test_dialog_lists_every_parameter_label(application, scoring_methods):
    text = "\n".join(dialog_texts(InfoDialog(scoring_methods)))
    for method in scoring_methods:
        for spec in method.parameter_specs:
            assert spec.label in text


def test_dialog_shows_choice_labels_and_ranges(application, scoring_methods):
    text = "\n".join(dialog_texts(InfoDialog(scoring_methods)))
    assert "default: Cosine similarity (-1 to 1)" in text
    assert "allowed 1 to 6" in text


def test_dialog_shows_every_paper_url(application, scoring_methods):
    text = "\n".join(dialog_texts(InfoDialog(scoring_methods)))
    for metric_info in METRIC_INFOS:
        for paper in metric_info.papers:
            assert paper.url in text


def test_dialog_papers_open_external_links(application, scoring_methods):
    dialog = InfoDialog(scoring_methods)
    paper_labels = [label for label in dialog.findChildren(QLabel) if label.objectName() == "infoPapers"]
    assert len(paper_labels) == sum(len(metric_info.papers) for metric_info in METRIC_INFOS)
    assert all(label.openExternalLinks() for label in paper_labels)


def test_dialog_is_a_parentless_window(application, scoring_methods):
    assert InfoDialog(scoring_methods).parentWidget() is None
