from __future__ import annotations

import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AgentStatus, ChatParticipantRole, ChatType, MediaType, MessageType, OperatingMode, PropertyStatus, VisibleContactType
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.security import now_utc
from app.models.chat import Chat
from app.models.chat_participant import ChatParticipant
from app.models.message import Message
from app.models.property import Property
from app.models.user import User
from app.repositories.agent_repository import AgentRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import ChatCreateRequest, ChatListItem, ChatParticipantResponse, MessageResponse, PropertyChatSummary
from app.services.storage_service import SupabaseStorageService


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chats = ChatRepository(session)
        self.agents = AgentRepository(session)
        self.properties = PropertyRepository(session)
        self.users = UserRepository(session)

    async def start_or_get_private_chat(self, *, current_user: User, payload: ChatCreateRequest) -> tuple[Chat, Message | None]:
        if not current_user.is_email_verified:
            raise ForbiddenError("Email verification required")
        property_obj: Property | None = None
        agent = None
        if payload.property_id:
            property_obj = await self.properties.get_public_by_id(payload.property_id)
            if not property_obj:
                raise NotFoundError("Property not found")
            if property_obj.status == PropertyStatus.HIDDEN.value or property_obj.deleted_at is not None:
                raise BadRequestError("Cannot start chat for unavailable property")
            agent = property_obj.agent
        elif payload.agent_id:
            agent = await self.agents.get_by_id(payload.agent_id)
        if not agent:
            raise NotFoundError("Agent not found")
        if payload.agent_id and payload.property_id and property_obj and property_obj.agent_id != agent.id:
            raise BadRequestError("Property does not belong to this agent")
        if agent.status != AgentStatus.APPROVED.value:
            raise ForbiddenError("You can only chat with approved agents")
        target_user_id = agent.user_id
        routed_through_noxer = False
        visible_contact_type = VisibleContactType.AGENT.value
        if agent.operating_mode == OperatingMode.NOXER_MANAGED.value:
            noxer_user = await self._get_noxer_contact_user()
            target_user_id = noxer_user.id
            routed_through_noxer = True
            visible_contact_type = VisibleContactType.NOXER.value
        if target_user_id == current_user.id:
            raise BadRequestError("You cannot start a chat with yourself")
        chat = await self.chats.get_private_chat_between(user_a_id=current_user.id, user_b_id=target_user_id, property_id=payload.property_id)
        created_message: Message | None = None
        if not chat:
            chat = Chat(chat_type=ChatType.PRIVATE.value, property_id=payload.property_id, created_by_id=current_user.id, target_user_id=target_user_id, underlying_agent_id=agent.id, routed_through_noxer=routed_through_noxer, visible_contact_type=visible_contact_type, title=property_obj.title if property_obj else None, last_message_at=None)
            await self.chats.add_chat(chat)
            now = now_utc()
            await self.chats.add_participant(ChatParticipant(chat_id=chat.id, user_id=current_user.id, role=ChatParticipantRole.MEMBER.value, joined_at=now))
            await self.chats.add_participant(ChatParticipant(chat_id=chat.id, user_id=target_user_id, role=ChatParticipantRole.MEMBER.value, joined_at=now))
        if payload.initial_message:
            created_message = await self._create_message(chat=chat, sender=current_user, content=payload.initial_message, message_type=MessageType.TEXT)
        await self.session.commit()
        await self.session.refresh(chat, attribute_names=["participants", "property", "target_user", "underlying_agent"])
        if created_message:
            await self.session.refresh(created_message, attribute_names=["sender"])
        return chat, created_message

    async def _get_noxer_contact_user(self) -> User:
        if settings.NOXER_CONTACT_USER_ID:
            try:
                user = await self.users.get_by_id(UUID(settings.NOXER_CONTACT_USER_ID))
            except ValueError:
                user = None
            if user and user.is_active:
                return user
        fallback = await self.users.get_first_active_super_admin()
        if not fallback:
            raise BadRequestError("NOXER_CONTACT_USER_ID is not configured and no active super admin exists")
        return fallback

    async def list_my_chats(self, *, current_user: User, page: int = 1, limit: int = 20) -> tuple[list[ChatListItem], int]:
        chats, total = await self.chats.list_user_chats(user_id=current_user.id, page=page, limit=limit)
        items: list[ChatListItem] = []
        for chat in chats:
            participant = await self.chats.get_participant(chat_id=chat.id, user_id=current_user.id)
            last_message = await self.chats.get_last_message(chat.id)
            unread_count = await self.chats.count_unread(chat_id=chat.id, user_id=current_user.id, last_read_at=participant.last_read_at if participant else None)
            items.append(ChatListItem(id=chat.id, chat_type=chat.chat_type, property_id=chat.property_id, created_by_id=chat.created_by_id, target_user_id=chat.target_user_id, underlying_agent_id=chat.underlying_agent_id, routed_through_noxer=chat.routed_through_noxer, visible_contact_type=chat.visible_contact_type, title=chat.title, last_message_id=chat.last_message_id, last_message_at=chat.last_message_at, created_at=chat.created_at, updated_at=chat.updated_at, participants=[ChatParticipantResponse.model_validate(p) for p in chat.participants], property=PropertyChatSummary(id=chat.property.id, title=chat.property.title, state=chat.property.state, community=chat.property.community) if chat.property else None, last_message=MessageResponse.model_validate(last_message) if last_message else None, unread_count=unread_count))
        return items, total

    async def get_chat_for_user(self, *, chat_id: UUID, current_user: User) -> Chat:
        participant = await self.chats.get_participant(chat_id=chat_id, user_id=current_user.id)
        if not participant:
            raise ForbiddenError("You are not a participant in this chat")
        chat = await self.chats.get_chat_by_id(chat_id)
        if not chat:
            raise NotFoundError("Chat not found")
        return chat

    async def list_messages(self, *, chat_id: UUID, current_user: User, page: int = 1, limit: int = 50) -> tuple[list[Message], int]:
        await self.get_chat_for_user(chat_id=chat_id, current_user=current_user)
        return await self.chats.list_messages(chat_id=chat_id, page=page, limit=limit)

    async def send_text_message(self, *, chat_id: UUID, current_user: User, content: str, client_message_id: str | None = None) -> Message:
        chat = await self.get_chat_for_user(chat_id=chat_id, current_user=current_user)
        message = await self._create_message(chat=chat, sender=current_user, content=content, message_type=MessageType.TEXT, client_message_id=client_message_id)
        await self.session.commit(); await self.session.refresh(message, attribute_names=["sender"])
        return message

    async def upload_media_message(self, *, chat_id: UUID, current_user: User, file: UploadFile, content: str | None = None, client_message_id: str | None = None) -> Message:
        chat = await self.get_chat_for_user(chat_id=chat_id, current_user=current_user)
        extension = Path(file.filename or "").suffix.lower()
        storage_path = f"chats/{chat_id}/{uuid.uuid4()}{extension}"
        uploaded = await SupabaseStorageService().upload_public_media(file=file, path=storage_path, allowed_media_types={MediaType.IMAGE, MediaType.VIDEO}, max_image_size_bytes=settings.MAX_CHAT_IMAGE_SIZE_MB * 1024 * 1024, max_video_size_bytes=settings.MAX_CHAT_VIDEO_SIZE_MB * 1024 * 1024)
        message_type = MessageType.IMAGE if uploaded.media_type == MediaType.IMAGE else MessageType.VIDEO
        message = await self._create_message(chat=chat, sender=current_user, content=content, message_type=message_type, media_url=uploaded.public_url, media_path=uploaded.path, media_content_type=uploaded.content_type, media_size_bytes=uploaded.size_bytes, client_message_id=client_message_id)
        await self.session.commit(); await self.session.refresh(message, attribute_names=["sender"])
        return message

    async def mark_chat_read(self, *, chat_id: UUID, current_user: User):
        participant = await self.chats.get_participant(chat_id=chat_id, user_id=current_user.id)
        if not participant:
            raise ForbiddenError("You are not a participant in this chat")
        read_at = now_utc()
        await self.chats.mark_read(participant=participant, read_at=read_at)
        await self.session.commit()
        return read_at

    async def _create_message(self, *, chat: Chat, sender: User, content: str | None, message_type: MessageType, media_url: str | None = None, media_path: str | None = None, media_content_type: str | None = None, media_size_bytes: int | None = None, client_message_id: str | None = None) -> Message:
        if message_type == MessageType.TEXT and not (content and content.strip()):
            raise BadRequestError("Text message content is required")
        message = Message(chat_id=chat.id, sender_id=sender.id, content=content.strip() if content else None, message_type=message_type.value, media_url=media_url, media_path=media_path, media_content_type=media_content_type, media_size_bytes=media_size_bytes, client_message_id=client_message_id)
        await self.chats.add_message(message)
        chat.last_message_id = message.id
        chat.last_message_at = message.created_at or now_utc()
        return message
