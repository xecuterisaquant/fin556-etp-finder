from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import re
from . import constants as C

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def _lower(s: str) -> str:
    return _norm(s).lower()

def _has(pattern: re.Pattern, text: str) -> bool:
    return bool(pattern.search(text))

def _single_stock_hint(name: str) -> bool:
    for pat in C.SINGLE_STOCK_PATTERNS:
        if pat.search(name):
            return True
    return False

def _is_inverse_context(name: str) -> bool:
    # Treat inverse only when not a duration/cash context
    if C.INVERSE.search(name):
        if C.EXCL_SHORT_DURATION.search(name):
            # Allow if explicit -1x/-2x or 'bear' appears outside duration context
            if re.search(r"\b(?:-1x|-2x|bear)\b", name, re.IGNORECASE):
                return True
            return False
        return True
    return False

def _is_leverage_context(name: str) -> bool:
    if C.LEVERAGE_NUM.search(name):
        return True
    # 'Ultra' alone is not sufficient; require brand + bull/bear or numeric x
    if C.BRAND_CTX.search(name) and (C.BULL_BEAR.search(name) or C.LEVERAGE_NUM.search(name)):
        return True
    return False

def _brand_implies_leverage(name: str) -> Tuple[bool, Optional[int], bool, List[str]]:
    """Return (hit, implied_mult, inverse_flag, reasons)."""
    reasons: List[str] = []
    implied_mult = None
    inverse = False
    hit = False

    if C.ULTRAPRO.search(name):
        hit = True
        implied_mult = 3
        reasons.append("brand_ultrapro_implies_3x")
    if C.PRO_ULTRA.search(name):
        hit = True
        implied_mult = 2
        reasons.append("brand_proshares_ultra_implies_2x")
    if C.PRO_ULTRASHORT.search(name):
        hit = True
        implied_mult = 2
        inverse = True
        reasons.append("brand_proshares_ultrashort_implies_minus2x")

    # If any brand hit, check for inverse tokens unless already set
    if hit and not inverse:
        if re.search(r"\b(inverse|ultra\s*short|short|bear)\b", name, re.IGNORECASE) and not C.EXCL_SHORT_DURATION.search(name):
            inverse = True
            reasons.append("inverse_keyword_under_brand")

    return hit, implied_mult, inverse, reasons

def _commodity_hit(name: str) -> bool:
    if "goldman" in name:
        return bool(re.search(r"\bgold(?!man)\b", name, re.IGNORECASE)) or bool(C.COMMODITY.search(name))
    return bool(C.COMMODITY.search(name))

def detect(name: str, row: Dict[str, str]) -> Tuple[bool, Optional[str], List[str], Optional[str]]:
    """
    Returns: (matched, category, reasons, etp_type)
    """
    reasons: List[str] = []
    raw_name = name
    name = _lower(name)

    # Global pre-filters
    etp_flag = (row.get("ETF", "").upper() == "Y")
    if etp_flag:
        reasons.append("etf_flag_Y")
    has_trust = _has(C.TRUST, name)
    has_etn = _has(C.ETN, name)
    has_etf_word = _has(C.ETF_WORD, name)

    plausible_etp = etp_flag or has_trust or has_etn or has_etf_word
    if not plausible_etp:
        return (False, None, [], None)

    # Determine etp_type
    etp_type = None
    if has_etn:
        etp_type = "ETN"
        reasons.append("type_etn_by_name")
    elif has_trust and _commodity_hit(name):
        etp_type = "Trust"
        reasons.append("type_trust_with_commodity")
    elif etp_flag or has_etf_word:
        etp_type = "ETF"
        reasons.append("type_etf")

    # Brand-only leverage inference first (to catch UltraPro/Ultra/UltraShort families)
    brand_hit, implied_mult, brand_inverse, brand_reasons = _brand_implies_leverage(name)
    if brand_hit:
        reasons.extend(brand_reasons)
        is_inverse = brand_inverse or _is_inverse_context(name)
        # Decide single-stock vs index by heuristic
        if _single_stock_hint(raw_name):
            cat = "leveraged_single_stock_inverse" if is_inverse else "leveraged_single_stock_long"
        else:
            cat = "leveraged_index_inverse" if is_inverse else "leveraged_index_long"
        reasons.append(f"implied_multiplier_{implied_mult}x" if implied_mult else "implied_multiplier_unknown")
        return (True, cat, reasons, etp_type or "ETF")

    # Category 1: Leverage/Inverse via explicit tokens
    is_leverage = _is_leverage_context(name)
    is_inverse = _is_inverse_context(name)
    if is_leverage or is_inverse:
        if _single_stock_hint(raw_name):
            cat = "leveraged_single_stock_inverse" if is_inverse else "leveraged_single_stock_long"
            if is_leverage: reasons.append("leverage_context")
            if is_inverse: reasons.append("inverse_context")
            reasons.append("single_stock_detected")
            return (True, cat, reasons, etp_type or "ETF")
        else:
            cat = "leveraged_index_inverse" if is_inverse else "leveraged_index_long"
            if is_leverage: reasons.append("leverage_context")
            if is_inverse: reasons.append("inverse_context")
            return (True, cat, reasons, etp_type or "ETF")

    # Category 2: Futures-based commodity/crypto
    if _commodity_hit(name) and _has(C.FUTURES, name):
        if re.search(r"\b(bitcoin|btc|ether|ethereum)\b", name, re.IGNORECASE):
            cat = "crypto_futures"
        else:
            cat = "commodity_futures"
        reasons.append("futures_keyword")
        return (True, cat, reasons, etp_type or ("ETN" if has_etn else "ETF"))

    # Category 3: Physically-backed commodity/crypto trusts/ETFs
    if has_trust and _commodity_hit(name):
        if re.search(r"\b(physical(ly)?|bullion|bars?)\b", name, re.IGNORECASE):
            reasons.append("physical_keyword")
        if re.search(r"\b(bitcoin|btc|ether|ethereum)\b", name, re.IGNORECASE):
            cat = "crypto_trust"
        else:
            cat = "commodity_physical_trust"
        return (True, cat, reasons, etp_type or "Trust")

    # Also allow physically-backed ETFs (non-trust) with explicit physical/bullion wording
    if _commodity_hit(name) and re.search(r"\b(physical(ly)?|bullion|bars?)\b", name, re.IGNORECASE):
        reasons.append("physical_keyword")
        if re.search(r"\b(bitcoin|btc|ether|ethereum)\b", name, re.IGNORECASE):
            cat = "crypto_trust"
        else:
            cat = "commodity_physical_trust"
        return (True, cat, reasons, etp_type or "ETF")

    return (False, None, [], etp_type)
