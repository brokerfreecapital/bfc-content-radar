"""Configured list of external RSS feeds to scan daily.

Edit this list to add/remove sources. Each entry should be a tuple of
(label, feed_url). Labels are used as the `source` field in ContentRecord.
"""

EXTERNAL_FEEDS = [
    ("hackernews", "https://hnrss.org/frontpage"),
    ("techmeme", "https://www.techmeme.com/feed.xml"),

    # Dow Jones / WSJ public RSS feeds
    ("wsj_us_business", "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness"),
    ("wsj_social_economy", "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed"),
    ("wsj_markets_main", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain"),

    # Financial Times
    ("ft_home", "https://www.ft.com/rss/home"),
    ("ft_markets", "https://www.ft.com/markets?format=rss"),

    # PYMNTS
    ("pymnts", "https://www.pymnts.com/rss/"),

    # Debanked
    ("debanked", "https://debanked.com/feed/"),

    # Small Business Trends
    ("smallbiz_trends", "https://feeds2.feedburner.com/SmallBusinessTrends"),

    # SMB / commerce blog feeds
    ("lightspeed", "https://www.lightspeedhq.com/blog/feed/"),
    ("fitsmallbusiness", "https://fitsmallbusiness.com/feed/"),

    # CNBC feeds
    ("cnbc_top_news", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=44877279"),
    ("cnbc_business", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"),
    ("cnbc_markets", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"),
    # Add industry/vertical feeds here, e.g.:
    # ("smb_lending_news", "https://example.com/smb-lending.rss"),
]
