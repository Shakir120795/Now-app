"""Bootstrap the first super-admin.

Usage (inside the api container or with env pointing at the DB):
    python -m scripts.create_admin --phone +919000000000 --name "Owner"

Creates the user if needed and grants the `super_admin` role. Sign in via the
normal OTP flow afterwards.
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.db.session import engine


async def main(phone: str, name: str | None) -> None:
    async with engine.begin() as conn:
        uid = (await conn.execute(
            text(
                """
                INSERT INTO users (phone, full_name, is_guest, referral_code)
                VALUES (:p, :n, false, upper(substr(md5(random()::text), 1, 8)))
                ON CONFLICT (phone) DO UPDATE SET full_name = COALESCE(EXCLUDED.full_name, users.full_name)
                RETURNING id
                """
            ),
            {"p": phone, "n": name},
        )).scalar_one()
        await conn.execute(
            text(
                """
                INSERT INTO user_roles (user_id, role_id)
                SELECT :uid, id FROM roles WHERE name = 'super_admin'
                ON CONFLICT DO NOTHING
                """
            ),
            {"uid": uid},
        )
    print(f"✓ super_admin granted to {phone} (user {uid})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phone", required=True)
    ap.add_argument("--name", default=None)
    args = ap.parse_args()
    asyncio.run(main(args.phone, args.name))
