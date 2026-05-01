from app.data.db import get_connection


class ContactsRepository:
    def upsert(self, name: str, email: str = "", whatsapp: str = "") -> None:
        clean_name = (name or "").strip()
        if not clean_name:
            return
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO contacts(name, email, whatsapp)
            VALUES(?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                email = CASE WHEN excluded.email != '' THEN excluded.email ELSE contacts.email END,
                whatsapp = CASE WHEN excluded.whatsapp != '' THEN excluded.whatsapp ELSE contacts.whatsapp END
            """,
            (clean_name, (email or "").strip(), (whatsapp or "").strip()),
        )
        conn.commit()
        conn.close()

    def get_email(self, name: str) -> str:
        key = (name or "").strip()
        if not key:
            return ""
        conn = get_connection()
        row = conn.execute(
            """
            SELECT email
            FROM contacts
            WHERE lower(name) = lower(?)
            LIMIT 1
            """,
            (key,),
        ).fetchone()
        conn.close()
        if not row:
            return ""
        return (row["email"] or "").strip()

    def get_whatsapp(self, name: str) -> str:
        key = (name or "").strip()
        if not key:
            return ""
        conn = get_connection()
        row = conn.execute(
            """
            SELECT whatsapp
            FROM contacts
            WHERE lower(name) = lower(?)
            LIMIT 1
            """,
            (key,),
        ).fetchone()
        conn.close()
        if not row:
            return ""
        return (row["whatsapp"] or "").strip()

    def find_name_candidates(self, fragment: str, limit: int = 5) -> list[dict]:
        q = (fragment or "").strip().lower()
        if not q:
            return []
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT name, email, whatsapp
            FROM contacts
            WHERE lower(name) LIKE ? COLLATE NOCASE
            ORDER BY name ASC
            LIMIT ?
            """,
            (f"%{q}%", limit),
        ).fetchall()
        conn.close()
        return [{"name": r["name"], "email": r["email"], "whatsapp": r["whatsapp"]} for r in rows]

    def find_email_candidates(self, fragment: str, limit: int = 5) -> list[dict]:
        q = (fragment or "").strip()
        if not q:
            return []
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT name, email, whatsapp
            FROM contacts
            WHERE lower(name) LIKE lower(?)
               OR lower(email) LIKE lower(?)
            ORDER BY name ASC
            LIMIT ?
            """,
            (f"%{q}%", f"%{q}%", limit),
        ).fetchall()
        conn.close()
        return [{"name": r["name"], "email": r["email"], "whatsapp": r["whatsapp"]} for r in rows]

    def resolve_email_alias(self, alias: str) -> str:
        key = (alias or "").strip()
        if not key:
            return ""
        conn = get_connection()
        row = conn.execute(
            """
            SELECT email
            FROM contacts
            WHERE lower(name) = lower(?)
               OR lower(email) = lower(?)
               OR lower(substr(email, 1, instr(email, '@') - 1)) = lower(?)
            LIMIT 1
            """,
            (key, key, key),
        ).fetchone()
        conn.close()
        if not row:
            return ""
        return (row["email"] or "").strip()
