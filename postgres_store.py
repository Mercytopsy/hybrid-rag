"""
A minimal LangChain BaseStore[str, bytes] backed by a Postgres table.

langchain_postgres does not ship a persistent byte store out of the box
(InMemoryByteStore is the usual default, but it's wiped on restart). This
gives MultiVectorRetriever a `byte_store` that survives container restarts,
keyed per collection so multiple retrievers can share one Postgres instance
without colliding.
"""
from typing import Iterator, List, Optional, Sequence, Tuple

import psycopg
from langchain_core.stores import BaseStore


class PostgresByteStore(BaseStore[str, bytes]):
    def __init__(self, connection_string: str, collection_name: str):
        self.collection_name = collection_name
        # langchain_postgres uses the SQLAlchemy-style "postgresql+psycopg://"
        # scheme; the psycopg driver itself only understands "postgresql://".
        self._conninfo = connection_string.replace("postgresql+psycopg://", "postgresql://")
        self._ensure_table()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._conninfo)

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS docstore (
                       collection_name TEXT NOT NULL,
                       key             TEXT NOT NULL,
                       value           BYTEA NOT NULL,
                       PRIMARY KEY (collection_name, key)
                   )"""
            )
            conn.commit()

    def mget(self, keys: Sequence[str]) -> List[Optional[bytes]]:
        if not keys:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM docstore WHERE collection_name = %s AND key = ANY(%s)",
                (self.collection_name, list(keys)),
            ).fetchall()
        found = {key: bytes(value) for key, value in rows}
        return [found.get(key) for key in keys]

    def mset(self, key_value_pairs: Sequence[Tuple[str, bytes]]) -> None:
        if not key_value_pairs:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                for key, value in key_value_pairs:
                    cur.execute(
                        """INSERT INTO docstore (collection_name, key, value)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (collection_name, key)
                           DO UPDATE SET value = EXCLUDED.value""",
                        (self.collection_name, key, value),
                    )
            conn.commit()

    def mdelete(self, keys: Sequence[str]) -> None:
        if not keys:
            return
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM docstore WHERE collection_name = %s AND key = ANY(%s)",
                (self.collection_name, list(keys)),
            )
            conn.commit()

    def yield_keys(self, *, prefix: Optional[str] = None) -> Iterator[str]:
        with self._connect() as conn:
            if prefix:
                rows = conn.execute(
                    "SELECT key FROM docstore WHERE collection_name = %s AND key LIKE %s",
                    (self.collection_name, f"{prefix}%"),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT key FROM docstore WHERE collection_name = %s",
                    (self.collection_name,),
                ).fetchall()
        for (key,) in rows:
            yield key
