"""Header text contracts: column headers may wrap at spaces but never split words.

The table is `table-fixed` with percentage widths, so at small widths headers
wrap. Splitting words mid-glyph (FREQUE / NCY) must not come back, in either
layout mode, and at desktop widths every header line must also fit its cell.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from conftest import _mock_data, open_dashboard_mode

COLUMNS = [
    "DX Callsign",
    "DX Location",
    "DXCC",
    "Spotter",
    "Band",
    "Frequency",
    "Mode/Comment",
    "Updated",
    "Source",
]

# A line break is a mid-word split when the last visible char of one line and
# the first visible char of the next are adjacent in the source text (no space
# between them). The line-break-only-at-spaces contract is checked per char.
HEADER_REPORT_JS = """
() => [...document.querySelectorAll('thead th')].map(th => {
    const walker = document.createTreeWalker(th, NodeFilter.SHOW_TEXT);
    let node = null;
    while (walker.nextNode()) {
        if (walker.currentNode.data.trim().length) { node = walker.currentNode; break; }
    }
    const data = node ? node.data : '';
    const range = document.createRange();
    const visible = [];
    for (let i = 0; i < data.length; i++) {
        if (!data[i].trim()) continue;
        range.setStart(node, i);
        range.setEnd(node, i + 1);
        const r = range.getBoundingClientRect();
        if (r.width < 0.5) continue;
        visible.push({ i, ch: data[i], top: r.top, right: r.right });
    }
    const lines = [];
    for (const c of visible) {
        let line = lines.length ? lines[lines.length - 1] : null;
        if (!line || Math.abs(c.top - line.top) > 2) {
            line = { text: '', maxRight: c.right, firstIdx: c.i, lastIdx: c.i };
            lines.push(line);
        } else if (c.i > line.lastIdx + 1) {
            line.text += ' '; // collapsed whitespace between visible chars
        }
        line.text += c.ch;
        line.maxRight = Math.max(line.maxRight, c.right);
        line.lastIdx = c.i;
    }
    const midWordSplits = [];
    for (let k = 1; k < lines.length; k++) {
        if (lines[k].firstIdx === lines[k - 1].lastIdx + 1) {
            midWordSplits.push(
                lines[k - 1].text + '|' + lines[k].text.slice(0, 1) + '...'
            );
        }
    }
    const cs = getComputedStyle(th);
    return {
        label: data.trim(),
        lines: lines.map(l => l.text),
        midWordSplits,
        lineMaxRight: Math.max(0, ...lines.map(l => l.maxRight)),
        cellRight: th.getBoundingClientRect().right,
        paddingRight: parseFloat(cs.paddingRight) || 0,
        overflowWrap: cs.overflowWrap,
        wordBreak: cs.wordBreak,
    };
})
"""


def _report(page):
    report = page.evaluate(HEADER_REPORT_JS)
    assert report, "expected table headers to be rendered"
    return report


DESKTOP_CASES = [(w, mode) for w in (1280, 1440, 1920) for mode in (False, True)]


@pytest.mark.parametrize("wide", [False, True])
@pytest.mark.parametrize("width", [1280, 1440, 1920])
def test_no_midword_splits_in_headers(page: Page, width, wide):
    """At desktop widths, no header word is ever broken across lines."""
    page.set_viewport_size({"width": width, "height": 800})
    open_dashboard_mode(page, wide, _mock_data(num_stations=5))
    for th in _report(page):
        assert th["midWordSplits"] == [], th["label"]
        for line in th["lines"]:
            assert line.strip(), f"{th['label']}: blank rendered line"


@pytest.mark.parametrize("wide", [False, True])
@pytest.mark.parametrize("width", [1280, 1440, 1920])
def test_single_word_headers_stay_on_one_line(page: Page, width, wide):
    """Labels without spaces (DXCC, Frequency, ...) never wrap."""
    page.set_viewport_size({"width": width, "height": 800})
    open_dashboard_mode(page, wide, _mock_data(num_stations=5))
    for th in _report(page):
        if " " not in th["label"]:
            assert len(th["lines"]) == 1, f"{th['label']} wrapped: {th['lines']}"


@pytest.mark.parametrize("wide", [False, True])
@pytest.mark.parametrize("width", [1280, 1440, 1920])
def test_header_lines_fit_their_cells(page: Page, width, wide):
    """Every rendered header line stays inside its cell (no bleed sideways)."""
    page.set_viewport_size({"width": width, "height": 800})
    open_dashboard_mode(page, wide, _mock_data(num_stations=5))
    for th in _report(page):
        assert th["lineMaxRight"] <= th["cellRight"] + 1, (
            f"{th['label']}: text passes the cell edge "
            f"({th['lineMaxRight']} > {th['cellRight']})"
        )


@pytest.mark.parametrize("wide", [False, True])
def test_no_midword_splits_at_narrow_width(page: Page, wide):
    """Even at 1024px, breaks happen only at whitespace, never inside words."""
    page.set_viewport_size({"width": 1024, "height": 800})
    open_dashboard_mode(page, wide, _mock_data(num_stations=5))
    for th in _report(page):
        assert th["midWordSplits"] == [], th["label"]


@pytest.mark.parametrize("wide", [False, True])
def test_wrapped_headers_contain_whole_words(page: Page, wide):
    """Headers that wrap at 1024px render lines made of whole word fragments.

    'MODE/COMMENT' may break after the slash, so tokens are split on both
    whitespace and slashes; mid-word integrity is asserted separately.
    """
    page.set_viewport_size({"width": 1024, "height": 800})
    open_dashboard_mode(page, wide, _mock_data(num_stations=5))
    for th in _report(page):
        tokens = set(re.split(r"[\s/]+", th["label"].upper()))
        for line in th["lines"]:
            for part in re.split(r"[\s/]+", line):
                assert part.upper() in tokens, (
                    f"{th['label']}: line {line!r} is not made of whole words"
                )


@pytest.mark.parametrize("wide", [False, True])
def test_header_css_forbids_forced_breaks(page: Page, wide):
    """No break-all/break-word/anywhere rules come back on header cells."""
    page.set_viewport_size({"width": 1280, "height": 800})
    open_dashboard_mode(page, wide, _mock_data(num_stations=5))
    for th in _report(page):
        assert th["wordBreak"] in ("normal", "keep-all"), th["label"]
        assert th["overflowWrap"] in ("normal", "break-spaces"), th["label"]


def test_all_expected_headers_render(page: Page):
    """The nine expected headers are present and rendered."""
    open_dashboard_mode(page, False, _mock_data(num_stations=5))
    headers = page.get_by_role("columnheader")
    expect(headers).to_have_count(len(COLUMNS))
    for i, name in enumerate(COLUMNS):
        expect(headers.nth(i)).to_have_text(name)
