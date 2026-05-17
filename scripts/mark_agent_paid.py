from __future__ import annotations

import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from app.core.enums import AgentStatus
from app.db.session import AsyncSessionLocal
from app.models.agent_profile import AgentProfile


async def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/mark_agent_paid.py "<agent_profile_id>"')
        raise SystemExit(1)

    agent_id = UUID(sys.argv[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AgentProfile).where(AgentProfile.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            print("Agent not found")
            raise SystemExit(1)

        agent.previous_status = agent.status
        agent.status = AgentStatus.PAID.value
        agent.status_note = "Manually marked as PAID for development testing before Paystack integration."
        await session.commit()
        print(f"Agent {agent.id} marked as PAID.")


if __name__ == "__main__":
    asyncio.run(main())
