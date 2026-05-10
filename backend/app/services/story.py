from __future__ import annotations

import logging
from collections.abc import Mapping

from psycopg import AsyncConnection

from app.exceptions import StoryGenerationError
from app.models.api import StoryGenerateRequest

logger = logging.getLogger(__name__)


async def generate_story(
    child: Mapping[str, object],
    request: StoryGenerateRequest,
    db: AsyncConnection,
) -> dict[str, object]:
    """C의 콘텐츠 생성 함수를 호출하고, 결과를 DB에 저장한다."""

    from app.llm.story_generator import generate_story_content

    content = await generate_story_content(child, request)

    row = await _save_story(
        db=db,
        user_id=str(child["user_id"]),
        child_id=str(child["id"]),
        title=content["title"],
        body=content["body"],
        lesson=content["lesson"],
    )
    return row


async def _save_story(
    *,
    db: AsyncConnection,
    user_id: str,
    child_id: str,
    title: str,
    body: str,
    lesson: str,
) -> dict[str, object]:
    async with db.cursor() as cur:
        await cur.execute(
            """
            insert into public.stories (user_id, child_id, title, body, lesson)
            values (%s::uuid, %s::uuid, %s, %s, %s)
            returning
                id::text as id,
                title,
                body,
                lesson,
                image_url,
                audio_url,
                created_at
            """,
            (user_id, child_id, title, body, lesson),
        )
        row = await cur.fetchone()

    await db.commit()

    if row is None:
        raise StoryGenerationError(
            "Failed to save story to database.", stage="finalize"
        )

    return dict(row)
