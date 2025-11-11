from __future__ import annotations

import pytest

try:
    from parsel import Selector
    from scrapy.http import HtmlResponse
except ModuleNotFoundError as exc:
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for parser tests.",
        allow_module_level=True,
    )

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
          <a
            href="http://ufcstats.com/fighter-details/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
          >
            John Doe
          </a>
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
    assert result["division"] == "Middleweight"
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
          <li><i>BIRTHPLACE:</i><span>Albuquerque, New Mexico, USA</span></li>
          <li><i>TRAINS AT:</i><span>Jackson Wink MMA</span></li>
        </ul>
        <div class="b-list__info-box b-list__info-box_style_middle-width js-guide clearfix">
          <div class="b-list__info-box-left clearfix">
            <div class="b-list__info-box-left">
              <i class="b-list__box-item-title">
                Career statistics:
              </i>
              <ul class="b-list__box-list b-list__box-list_margin-top">
                <li class="b-list__box-list-item b-list__box-list-item_type_block">
                  <i
                    class="b-list__box-item-title
                           b-list__box-item-title_font_lowercase
                           b-list__box-item-title_type_width"
                  >
                    SLpM:
                  </i>
                  5.35
                </li>
                <li class="b-list__box-list-item b-list__box-list-item_type_block">
                  <i
                    class="b-list__box-item-title
                           b-list__box-item-title_font_lowercase
                           b-list__box-item-title_type_width"
                  >
                    Str. Acc.:
                  </i>
                  50%
                </li>
                <li class="b-list__box-list-item b-list__box-list-item_type_block">
                  <i
                    class="b-list__box-item-title
                           b-list__box-item-title_font_lowercase
                           b-list__box-item-title_type_width"
                  >
                    SApM:
                  </i>
                  3.10
                </li>
                <li class="b-list__box-list-item b-list__box-list-item_type_block">
                  <i
                    class="b-list__box-item-title
                           b-list__box-item-title_font_lowercase
                           b-list__box-item-title_type_width"
                  >
                    Str. Def.:
                  </i>
                  55%
                </li>
              </ul>
            </div>
            <div class="b-list__info-box-right b-list__info-box_style-margin-right">
              <ul class="b-list__box-list b-list__box-list_margin-top">
                <li class="b-list__box-list-item b-list__box-list-item_type_block">
                  <i
                    class="b-list__box-item-title
                           b-list__box-item-title_font_lowercase
                           b-list__box-item-title_type_width"
                  >
                    TD Avg.:
                  </i>
                  2.00
                </li>
                <li class="b-list__box-list-item b-list__box-list-item_type_block">
                  <i
                    class="b-list__box-item-title
                           b-list__box-item-title_font_lowercase
                           b-list__box-item-title_type_width"
                  >
                    TD Acc.:
                  </i>
                  40%
                </li>
                <li class="b-list__box-list-item b-list__box-list-item_type_block">
                  <i
                    class="b-list__box-item-title
                           b-list__box-item-title_font_lowercase
                           b-list__box-item-title_type_width"
                  >
                    TD Def.:
                  </i>
                  75%
                </li>
                <li class="b-list__box-list-item b-list__box-list-item_type_block">
                  <i
                    class="b-list__box-item-title
                           b-list__box-item-title_font_lowercase
                           b-list__box-item-title_type_width"
                  >
                    Sub. Avg.:
                  </i>
                  1.2
                </li>
              </ul>
            </div>
          </div>
        </div>
        <table class="b-fight-details__table">
          <tbody>
            <tr class="b-fight-details__table-row">
              <td>
                <a
                  href="http://ufcstats.com/fight-details/99999999-aaaa-bbbb-cccc-dddddddddddd"
                >
                  W
                </a>
              </td>
              <td>
                <p>
                  <a
                    href="http://ufcstats.com/fighter-details/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                  >
                    John Doe
                  </a>
                </p>
                <p>
                  <a
                    href="http://ufcstats.com/fighter-details/bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
                  >
                    Jane Smith
                  </a>
                </p>
              </td>
              <td>
                <p>1</p>
                <p>0</p>
              </td>
              <td>
                <p>55</p>
                <p>40</p>
              </td>
              <td>
                <p>3</p>
                <p>1</p>
              </td>
              <td>
                <p>1</p>
                <p>0</p>
              </td>
              <td>
                <p>
                  <a
                    href="http://ufcstats.com/event-details/eeeeeeee-ffff-gggg-hhhh-iiiiiiiiiiii"
                  >
                    UFC 300
                  </a>
                </p>
                <p>Apr 13, 2024</p>
              </td>
              <td>
                <p>KO/TKO</p>
              </td>
              <td>
                <p>2</p>
              </td>
              <td>
                <p>03:15</p>
              </td>
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
    assert detail["division"] == "Middleweight"
    assert detail["birthplace"] == "Albuquerque, New Mexico, USA"
    assert detail["fighting_out_of"] == "Jackson Wink MMA"
    assert detail["striking"]["slpm"] == "5.35"
    assert detail["striking"]["str_acc"] == "50%"
    assert detail["grappling"]["td_avg"] == "2.00"
    assert detail["grappling"]["td_acc"] == "40%"
    fight = detail["fight_history"][0]
    assert fight["fight_id"] == "99999999-aaaa-bbbb-cccc-dddddddddddd"
    assert fight["opponent_id"] == "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
    assert fight["event_name"] == "UFC 300"
    assert fight["event_date"] == "2024-04-13"
    assert fight["result"] == "W"
    assert fight["method"] == "KO/TKO"
    assert fight["round"] == 2
    assert fight["time"] == "03:15"
    assert fight["stats"]["knockdowns"] == "1"
    assert fight["stats"]["total_strikes"] == "55"
    assert fight["stats"]["takedowns"] == "3"
    assert fight["stats"]["submissions"] == "1"


def test_parse_fighter_detail_page_prefers_scraped_division():
    html = """
    <html>
      <body>
        <div class="b-content__banner">
          <span class="b-content__title-highlight">Jane Doe</span>
        </div>
        <div class="b-fight-details__person">
          <i>Featherweight</i>
        </div>
        <ul class="b-list__box-list">
          <li><i>Weight:</i><span>155 lbs.</span></li>
        </ul>
      </body>
    </html>
    """
    response = HtmlResponse(
        url="http://ufcstats.com/fighter-details/bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
        body=html,
        encoding="utf-8",
    )

    detail = parser.parse_fighter_detail_page(response)

    assert detail["division"] == "Featherweight"
    assert detail["weight"] == "155 lbs."


def test_parse_fighter_detail_page_fallback_fighting_out_of():
    """Test that 'FIGHTING OUT OF' is used as fallback when 'TRAINS AT' is missing."""
    html = """
    <html>
      <body>
        <div class="b-content__banner">
          <span class="b-content__title-highlight">Jane Smith</span>
        </div>
        <ul class="b-list__box-list">
          <li><i>Weight:</i><span>135 lbs.</span></li>
          <li><i>BIRTHPLACE:</i><span>Rio de Janeiro, Brazil</span></li>
          <li><i>FIGHTING OUT OF:</i><span>American Top Team</span></li>
        </ul>
      </body>
    </html>
    """
    response = HtmlResponse(
        url="http://ufcstats.com/fighter-details/dddddddd-eeee-ffff-0000-111111111111",
        body=html,
        encoding="utf-8",
    )

    detail = parser.parse_fighter_detail_page(response)

    assert detail["birthplace"] == "Rio de Janeiro, Brazil"
    assert detail["fighting_out_of"] == "American Top Team"


def test_parse_fighter_detail_page_geography_fields_missing():
    """Test that geography fields are None when not present in the HTML."""
    html = """
    <html>
      <body>
        <div class="b-content__banner">
          <span class="b-content__title-highlight">Unknown Fighter</span>
        </div>
        <ul class="b-list__box-list">
          <li><i>Weight:</i><span>170 lbs.</span></li>
        </ul>
      </body>
    </html>
    """
    response = HtmlResponse(
        url="http://ufcstats.com/fighter-details/eeeeeeee-ffff-0000-1111-222222222222",
        body=html,
        encoding="utf-8",
    )

    detail = parser.parse_fighter_detail_page(response)

    assert detail["birthplace"] is None
    assert detail["fighting_out_of"] is None


def test_parse_fight_history_stats_handles_missing_values():
    html = """
    <html>
      <body>
        <table class="b-fight-details__table">
          <tbody>
            <tr class="b-fight-details__table-row">
              <td></td>
              <td></td>
              <td><p>--</p><p>--</p></td>
              <td><p>--</p><p>--</p></td>
              <td><p>--</p><p>--</p></td>
              <td><p>--</p><p>--</p></td>
              <td></td>
              <td></td>
              <td></td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """
    response = HtmlResponse(
        url="http://ufcstats.com/fighter-details/cccccccc-dddd-eeee-ffff-000000000000",
        body=html,
        encoding="utf-8",
    )

    detail = parser.parse_fighter_detail_page(response)

    stats = detail["fight_history"][0]["stats"]
    assert stats["knockdowns"] is None
    assert stats["total_strikes"] is None
    assert stats["takedowns"] is None
    assert stats["submissions"] is None
