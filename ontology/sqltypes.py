"""ontology/sqltypes.py — tipos SQL compartidos por los modelos del libro y de gobernanza (módulo HOJA: no importa
ningún modelo; lo importan ontology/ledger_models.py y ontology/governance_models.py).

Antes vivían en ledger_models y governance_models los importaba de ahí: `import ontology.ledger_models` en primer
lugar fallaba por la importación circular ledger_models → models → governance_models → ledger_models (a medio cargar,
sin XID8). Con los tipos aquí cualquier orden de importación funciona.

`txid` usa el tipo xid8 + DEFAULT pg_current_xact_id() desde Postgres 13 (Railway usa 16); en una base más vieja se
compila como bigint + txid_current() (core/ledger_ddl.detect_xid8 corre ANTES de create_all).
"""
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.types import UserDefinedType


class XID8(UserDefinedType):
    """xid8 (o bigint en Postgres < 13). Solo DDL: el código lo escribe por DEFAULT y lo lee como texto."""
    cache_ok = True

    def get_col_spec(self, **kw):
        from core import ledger_ddl
        return ledger_ddl._txid_type()


class txid_default(FunctionElement):      # noqa: N801 — se usa como valor de server_default
    """DEFAULT pg_current_xact_id() (o txid_current()) según la base."""
    inherit_cache = True


@compiles(txid_default)
def _compile_txid_default(element, compiler, **kw):
    from core import ledger_ddl
    return ledger_ddl.txid_expr()
