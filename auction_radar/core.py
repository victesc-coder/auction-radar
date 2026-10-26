"""Regras do radar. Valores monetários usam Decimal, nunca float."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional
from zoneinfo import ZoneInfo

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def money(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Valor monetário inválido") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Valores devem ser finitos e não negativos")
    return result


@dataclass(frozen=True)
class Lot:
    source: str
    lot_id: str
    title: str
    url: str
    state: str
    city: str
    auction_at: Optional[datetime]
    bid: Decimal
    resale: Optional[Decimal]
    costs: Decimal
    commission: Decimal

    @classmethod
    def from_dict(cls, row):
        required = ("source", "lot_id", "title", "url", "state", "city")
        for key in required:
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError("Campo obrigatório: " + key)
        timestamp = row.get("auction_at")
        when = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else None
        if when is not None and when.utcoffset() is None:
            raise ValueError("auction_at precisa incluir o fuso horário")
        commission = money(row["commission_rate"])
        if commission > 1:
            raise ValueError("commission_rate deve estar entre 0 e 1")
        return cls(*(row[k].strip() for k in required[:4]),
                   row["state"].strip().upper(), row["city"].strip(), when,
                   money(row["bid"]), money(row["resale_estimate"]) if row.get("resale_estimate") is not None else None,
                   money(row["additional_costs"]), commission)


def eligible(lot, now, days=7):
    if now.utcoffset() is None:
        raise ValueError("O horário de referência precisa incluir o fuso")
    if days < 1:
        raise ValueError("O horizonte deve ser positivo")
    return (lot.state == "SP" and lot.auction_at is not None
            and now <= lot.auction_at < now + timedelta(days=days))


def analyze(lot, target_margin=Decimal("0.20")):
    """Margem = lucro / revenda. Custos incluem todas as despesas além da comissão."""
    target_margin = money(target_margin)
    if target_margin >= 1:
        raise ValueError("A margem deve estar entre 0 e 1, exclusive 1")
    total = lot.bid * (1 + lot.commission) + lot.costs
    def amount(value):
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    result = {"estimated_total": amount(total), "estimated_profit": None,
              "estimated_margin": None, "maximum_bid": None, "within_target": None}
    if lot.resale is None or lot.resale == 0:
        return result
    profit = lot.resale - total
    ceiling = (lot.resale * (1 - target_margin) - lot.costs) / (1 + lot.commission)
    result.update(estimated_profit=amount(profit), estimated_margin=str(profit / lot.resale),
                  maximum_bid=str(max(Decimal(0), ceiling).quantize(Decimal("0.01"), rounding=ROUND_DOWN)),
                  within_target=profit / lot.resale >= target_margin)
    return result
