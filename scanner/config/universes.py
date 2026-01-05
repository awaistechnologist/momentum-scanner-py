"""Pre-defined universe lists for scanning."""

# FTSE 100 constituents (top liquid UK stocks)
UK_LARGE_CAP = [
    "SHEL.L",    # Shell
    "AZN.L",     # AstraZeneca
    "HSBA.L",    # HSBC
    "ULVR.L",    # Unilever
    "DGE.L",     # Diageo
    "BP.L",      # BP
    "GSK.L",     # GSK
    "RIO.L",     # Rio Tinto
    "BATS.L",    # British American Tobacco
    "LSEG.L",    # London Stock Exchange Group
    "REL.L",     # RELX
    "NG.L",      # National Grid
    "LLOY.L",    # Lloyds Banking Group
    "VOD.L",     # Vodafone
    "BARC.L",    # Barclays
    "PRU.L",     # Prudential
    "BT.L",      # BT Group
    "RKT.L",     # Reckitt
    "AAL.L",     # Anglo American
    "CRH.L",     # CRH
    "GLEN.L",    # Glencore
    "AV.L",      # Aviva
    "SSE.L",     # SSE
    "TSCO.L",    # Tesco
    "LGEN.L",    # Legal & General
    "NWG.L",     # NatWest Group
    "STAN.L",    # Standard Chartered
    "IMB.L",     # Imperial Brands
    "CPG.L",     # Compass Group
    "SMT.L",     # Scottish Mortgage Investment Trust
]

# US Liquid Tech stocks (high volume, well-known)
US_LIQUID_TECH = [
    "AAPL",      # Apple
    "MSFT",      # Microsoft
    "GOOGL",     # Alphabet (Google)
    "AMZN",      # Amazon
    "NVDA",      # NVIDIA
    "META",      # Meta (Facebook)
    "TSLA",      # Tesla
    "AMD",       # Advanced Micro Devices
    "NFLX",      # Netflix
    "ADBE",      # Adobe
    "CRM",       # Salesforce
    "INTC",      # Intel
    "CSCO",      # Cisco
    "ORCL",      # Oracle
    "AVGO",      # Broadcom
    "QCOM",      # Qualcomm
    "NOW",       # ServiceNow
    "SNOW",      # Snowflake
    "PLTR",      # Palantir
    "UBER",      # Uber
    "PYPL",      # PayPal
    "SHOP",      # Shopify
    "ZM",        # Zoom
    "DOCU",      # DocuSign
]

# US Blue Chips (major non-tech)
US_BLUE_CHIP = [
    "JPM",       # JPMorgan Chase
    "V",         # Visa
    "MA",        # Mastercard
    "JNJ",       # Johnson & Johnson
    "WMT",       # Walmart
    "PG",        # Procter & Gamble
    "UNH",       # UnitedHealth
    "HD",        # Home Depot
    "DIS",       # Disney
    "BAC",       # Bank of America
    "KO",        # Coca-Cola
    "PFE",       # Pfizer
    "XOM",       # Exxon Mobil
    "CVX",       # Chevron
    "MRK",       # Merck
    "COST",      # Costco
    "NKE",       # Nike
    "BA",        # Boeing
    "GE",        # General Electric
    "CAT",       # Caterpillar
]

# US Growth & Mid-Cap Stocks
US_GROWTH = [
    "ABNB",      # Airbnb
    "COIN",      # Coinbase
    "RBLX",      # Roblox
    "DASH",      # DoorDash
    "DDOG",      # Datadog
    "NET",       # Cloudflare
    "CRWD",      # CrowdStrike
    "ZS",        # Zscaler
    "OKTA",      # Okta
    "MDB",       # MongoDB
    "TEAM",      # Atlassian
    "WDAY",      # Workday
    "PANW",      # Palo Alto Networks
    "FTNT",      # Fortinet
    "SPLK",      # Splunk
    "TWLO",      # Twilio
    "ROKU",      # Roku
    "SQ",        # Block (moved from tech)
    "SPOT",      # Spotify
    "U",         # Unity Software
]

# US Financial & Industrial
US_FINANCIAL = [
    "GS",        # Goldman Sachs
    "MS",        # Morgan Stanley
    "C",         # Citigroup
    "WFC",       # Wells Fargo
    "BLK",       # BlackRock
    "SCHW",      # Charles Schwab
    "AXP",       # American Express
    "SPGI",      # S&P Global
    "MMC",       # Marsh & McLennan
    "ICE",       # Intercontinental Exchange
]

# US Healthcare & Pharma
US_HEALTHCARE = [
    "ABBV",      # AbbVie
    "TMO",       # Thermo Fisher
    "ABT",       # Abbott Labs
    "DHR",       # Danaher
    "LLY",       # Eli Lilly
    "BMY",       # Bristol Myers Squibb
    "AMGN",      # Amgen
    "GILD",      # Gilead Sciences
    "VRTX",      # Vertex Pharma
    "REGN",      # Regeneron
    "ISRG",      # Intuitive Surgical
    "CI",        # Cigna
    "CVS",       # CVS Health
    "HUM",       # Humana
    "BIIB",      # Biogen
    "ZTS",       # Zoetis
    "ILMN",      # Illumina
    "IDXX",      # Idexx Labs
    "DXCM",      # DexCom
    "ALGN",      # Align Technology
    "EXAS",      # Exact Sciences
    "STE",       # Steris
]


# Mapping of list names to symbols
UNIVERSE_LISTS = {
    "UK_LARGE_CAP": UK_LARGE_CAP,
    "US_LIQUID_TECH": US_LIQUID_TECH,
    "US_BLUE_CHIP": US_BLUE_CHIP,
    "US_GROWTH": US_GROWTH,
    "US_FINANCIAL": US_FINANCIAL,
    "US_HEALTHCARE": US_HEALTHCARE,
}


def get_universe(list_names: list[str], custom_symbols: list[str] = None) -> list[str]:
    """
    Get combined universe from list names and custom symbols.

    Args:
        list_names: List of predefined universe names
        custom_symbols: Additional custom symbols

    Returns:
        Combined list of unique symbols
    """
    symbols = set()

    # Add symbols from named lists
    for list_name in list_names:
        if list_name in UNIVERSE_LISTS:
            symbols.update(UNIVERSE_LISTS[list_name])
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Unknown universe list: {list_name}")

    # Add custom symbols
    if custom_symbols:
        symbols.update(custom_symbols)

    return sorted(list(symbols))
