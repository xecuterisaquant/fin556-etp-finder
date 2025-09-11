import re

# Source URL for nasdaqtraded.txt
NASDAQ_TRADED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"

# Core regex snippets (compiled once)
LEVERAGE_NUM = re.compile(r"\b(?:1\.5|2|3|4)x\b", re.IGNORECASE)
INVERSE = re.compile(r"\b(?:-1x|-2x|inverse|short|bear)\b", re.IGNORECASE)
BRAND_CTX = re.compile(r"(?:\bultrapro\b|\bproshares\s+ultra\b|\bdirexion\s+daily\b)", re.IGNORECASE)
BULL_BEAR = re.compile(r"\b(?:bull|bear)\b", re.IGNORECASE)

# Expanded duration/credit/cash exclusions to prevent false inverse triggers
EXCL_SHORT_DURATION = re.compile(
    r"\b(?:ultra\s*short|short[-\s]?)"
    r"(?:term|duration|maturit(?:y|ies)|treasury|t-?bill|muni|municipal|"
    r"government|gov(?:'t)?|corp(?:orate)?|bond|fixed\s*income|income|cash|money\s*market)\b",
    re.IGNORECASE
)

COMMODITY = re.compile(r"\b(gold|silver|platinum|palladium|oil|crude|brent|wti|natural\s+gas|nat\s+gas|vix|bitcoin|btc|ether|ethereum|copper)\b", re.IGNORECASE)
FUTURES = re.compile(r"\bfutures?\b|\bfront-?month\b|\bfutures?\s+strategy\b|\bstrategy\b", re.IGNORECASE)
TRUST = re.compile(r"\btrust\b", re.IGNORECASE)
EXCL_GOLDMAN = re.compile(r"\bgold(?!man)\b", re.IGNORECASE)
ETN = re.compile(r"\betns?\b|\bexchange-?traded\s+notes?\b|\bnotes?\s+due\b", re.IGNORECASE)
ETF_WORD = re.compile(r"\betf(s)?\b", re.IGNORECASE)

# Brand-only leverage inference
ULTRAPRO = re.compile(r"\bultrapro\b", re.IGNORECASE)           # implies 3x family
PRO_ULTRA = re.compile(r"\bproshares\s+ultra\b", re.IGNORECASE)  # implies 2x long unless inverse tokens present
PRO_ULTRASHORT = re.compile(r"\bproshares\s+ultrashort\b", re.IGNORECASE)  # implies -2x inverse

# Single-stock cues
SINGLE_STOCK_PATTERNS = [
    re.compile(r"\bdaily\s+([A-Z]{1,5})\s+(bull|bear)\b", re.IGNORECASE),
    re.compile(r"\b(?:long|short)\s+([A-Z]{1,5})\b", re.IGNORECASE),
    re.compile(r"\b([A-Z]{1,5})\b\s+(?:bull|bear)\s+(?:1x|2x|3x|-1x|-2x)\b", re.IGNORECASE),
    re.compile(r"\b([A-Z]{1,5})\)\s*(?:bull|bear)", re.IGNORECASE),
]

EXPECTED_COLUMNS = [
    "Nasdaq Traded","Symbol","Security Name","Listing Exchange","Market Category",
    "ETF","Round Lot Size","Test Issue","Financial Status","CQS Symbol",
    "NASDAQ Symbol","NextShares"
]
