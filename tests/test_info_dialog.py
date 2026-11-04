import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from presentation.views.info_content import METRIC_INFOS
from presentation.views.info_dialog import InfoDialog


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def test_every_metric_cites_at_least_one_paper_with_a_link():
    for metric_info in METRIC_INFOS:
        assert metric_info.papers
        for paper in metric_info.papers:
            assert paper.url.startswith("https://")


def test_dialog_shows_every_metric_name(application):
    dialog = InfoDialog()
    texts = {label.text() for label in dialog.findChildren(QLabel)}
    for metric_info in METRIC_INFOS:
        assert metric_info.name in texts


def test_dialog_papers_open_external_links(application):
    dialog = InfoDialog()
    paper_labels = [label for label in dialog.findChildren(QLabel) if label.objectName() == "infoPapers"]
    assert len(paper_labels) == sum(len(metric_info.papers) for metric_info in METRIC_INFOS)
    assert all(label.openExternalLinks() for label in paper_labels)
