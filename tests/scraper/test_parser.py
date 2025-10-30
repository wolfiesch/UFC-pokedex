from __future__ import annotations

import pytest

parsel = pytest.importorskip("parsel")
scrapy_http = pytest.importorskip("scrapy.http")

from parsel import Selector
from scrapy.http import HtmlResponse

from scraper.utils import parser


def _load_selector(html: str, query: str):
    doc = Selector(text=html)
    nodes = doc.css(query)
    assert nodes, f"No nodes matched selector {query}"
    return nodes[0]


def test_parse_fighter_list_row():
    html = """
    <table>
      <tr class="b-statistics__table-row">
        <td>
          <a href="http://ufcstats.com/fighter-details/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee">John Doe</a>
          <span class="b-statistics__nickname">The Hammer</span>
        </td>
        <td><p>6' 0"</p></td>
        <td><p>185 lbs.</p></td>
        <td><p>75"</p></td>
        <td><p>Orthodox</p></td>
        <td><p>Jun 15, 1990</p></td>
      </tr>
    </table>
    """
    row = _load_selector(html, "tr.b-statistics__table-row")

    result = parser.parse_fighter_list_row(row)

    assert result["fighter_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert result["name"] == "John Doe"
    assert result["nickname"] == "The Hammer"
    assert result["height"] == '6\' 0"'
    assert result["weight"] == "185 lbs."
    assert result["stance"] == "Orthodox"
    assert result["dob"] == "1990-06-15"


def test_parse_fighter_detail_page():
    html = """
    <html>
      <body>
        <div class="b-content__banner">
          <span class="b-content__title-highlight">John Doe</span>
          <span class="b-content__Nickname">The Hammer</span>
          <span class="b-content__title-record">Record: 10-2-0 (W-L-D)</span>
        </div>
        <ul class="b-list__box-list">
          <li><i>Height:</i><span>6' 0"</span></li>
          <li><i>Weight:</i><span>185 lbs.</span></li>
          <li><i>Reach:</i><span>75"</span></li>
          <li><i>Leg Reach:</i><span>40"</span></li>
          <li><i>STANCE:</i><span>Orthodox</span></li>
          <li><i>DOB:</i><span>Jun 15, 1990</span></li>
          <li><i>AGE:</i><span>33</span></li>
        </ul>
        <section class="b-list__info-box">
          <h2>Striking</h2>
          <ul>
            <li><i>SLpM:</i><strong>5.35</strong></li>
            <li><i>Str. Acc.:</i><strong>50%</strong></li>
          </ul>
        </section>
        <section class="b-list__info-box">
          <h2>Grappling</h2>
          <ul>
            <li><i>TDAvg.:</i><strong>2.00</strong></li>
            <li><i>TD Acc.:</i><strong>40%</strong></li>
          </ul>
        </section>
        <table class="b-fight-details__table">
          <tbody>
            <tr class="b-fight-details__table-row">
              <td>
                W
                <a href="http://ufcstats.com/fight-details/99999999-aaaa-bbbb-cccc-dddddddddddd">Details</a>
              </td>
              <td>
                <a href="http://ufcstats.com/fighter-details/bbbbbbbb-cccc-dddd-eeee-ffffffffffff">Jane Smith</a>
              </td>
              <td>50 of 100</td>
              <td>50%</td>
              <td>60 of 120</td>
              <td>2 of 5</td>
              <td>
                <a href="http://ufcstats.com/event-details/eeeeeeee-ffff-gggg-hhhh-iiiiiiiiiiii">UFC 300</a>
                <span>Apr 13, 2024</span>
              </td>
              <td>KO/TKO</td>
              <td>2</td>
              <td>03:15</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """
    response = HtmlResponse(
        url="http://ufcstats.com/fighter-details/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        body=html,
        encoding="utf-8",
    )

    detail = parser.parse_fighter_detail_page(response)

    assert detail["fighter_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert detail["name"] == "John Doe"
    assert detail["nickname"] == "The Hammer"
    assert detail["record"] == "10-2-0 (W-L-D)"
    assert detail["height"] == '6\' 0"'
    assert detail["weight"] == "185 lbs."
    assert detail["leg_reach"] == '40"'
    assert detail["stance"] == "Orthodox"
    assert detail["dob"] == "1990-06-15"
    assert detail["age"] == 33
    assert detail["striking"]["slpm"] == "5.35"
    assert detail["grappling"]["tdavg"] == "2.00"
    fight = detail["fight_history"][0]
    assert fight["fight_id"] == "99999999-aaaa-bbbb-cccc-dddddddddddd"
    assert fight["opponent_id"] == "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
    assert fight["event_name"] == "UFC 300"
    assert fight["event_date"] == "2024-04-13"
    assert fight["result"] == "W"
    assert fight["method"] == "KO/TKO"
    assert fight["round"] == 2
    assert fight["time"] == "03:15"
