"""Importação explícita de JSON; não realiza coleta automática."""
import argparse
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

from .core import Lot, SAO_PAULO, analyze, eligible


def run(input_path, database, now, days, margin):
    rows = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("O arquivo deve conter uma lista de lotes")
    # Valida todo o lote de entrada antes de alterar o histórico.
    lots = []
    for index, row in enumerate(rows, 1):
        try:
            lots.append(Lot.from_dict(row))
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Lote %s: %s" % (index, exc)) from exc
    reports = []
    for lot in lots:
        if eligible(lot, now, days):
            reports.append({"source": lot.source, "lot_id": lot.lot_id, "title": lot.title,
                            "city": lot.city, "url": lot.url,
                            "auction_at": lot.auction_at.isoformat(), **analyze(lot, margin)})
    with sqlite3.connect(database) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS observations (
            source TEXT NOT NULL, lot_id TEXT NOT NULL, observed_at TEXT NOT NULL,
            payload TEXT NOT NULL,
            UNIQUE(source, lot_id, observed_at, payload))""")
        for lot in lots:
            payload = json.dumps(asdict(lot), default=str, sort_keys=True, ensure_ascii=False)
            db.execute("INSERT OR IGNORE INTO observations VALUES (?, ?, ?, ?)",
                       (lot.source, lot.lot_id, now.isoformat(), payload))
    reports.sort(key=lambda r: datetime.fromisoformat(r["auction_at"]))
    return {"observed_at": now.isoformat(), "imported": len(lots),
            "eligible": len(reports), "lots": reports}


def main():
    parser = argparse.ArgumentParser(description="Radar de veículos: importação e análise local")
    parser.add_argument("input", help="Arquivo JSON de lotes")
    parser.add_argument("--database", default="radar.sqlite3")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--margin", default="0.20", help="Lucro / revenda desejado (0.20 = 20%%)")
    parser.add_argument("--now", help="Data ISO com fuso, para execução reproduzível")
    args = parser.parse_args()
    try:
        now = datetime.fromisoformat(args.now) if args.now else datetime.now(SAO_PAULO)
        margin = Decimal(args.margin)
        if not margin.is_finite() or not 0 <= margin < 1:
            raise ValueError("A margem deve estar entre 0 e 1, exclusive 1")
        if args.days < 1 or now.utcoffset() is None:
            raise ValueError("Informe dias positivos e data com fuso horário")
        result = run(args.input, args.database, now, args.days, margin)
    except (ValueError, ArithmeticError, OSError, sqlite3.Error) as exc:
        parser.exit(2, "Erro: %s\n" % exc)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
