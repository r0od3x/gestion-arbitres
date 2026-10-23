"""Configuration du logging. Ne jamais journaliser de jeton complet."""

import logging
import sys

_SENSITIVE_PREFIXES = ("Bearer ", "EAA")


class RedactTokensFilter(logging.Filter):
    """Tronque les valeurs ressemblant à des jetons dans les messages de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for prefix in _SENSITIVE_PREFIXES:
            index = message.find(prefix)
            if index != -1:
                keep = index + len(prefix) + 6
                record.msg = message[:keep] + "…[tronqué]"
                record.args = ()
                break
        return True


def setup_logging(debug: bool = False) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s"))
    handler.addFilter(RedactTokensFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
