from __future__ import annotations

import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import (
    AgentStatus,
    ChatParticipantRole,
    ChatType,
    MediaType,
    MessageType,
    OperatingMode,
    PropertyStatus,
    UserRole,
    VisibleContactType,
)
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
from app.schemas.chat import (
    ChatCreateRequest,
    ChatListItem,
    ChatParticipantResponse,
    GroupChatCreateRequest,
    GroupChatListItem,
    MessageResponse,
    PropertyChatSummary,
)
from app.services.agent_service import AgentService
from app.services.storage_service import SupabaseStorageService


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chats = ChatRepository(session)
        self.agents = AgentRepository(session)
        self.properties = PropertyRepository(session)
        self.users = UserRepository(session)
        self.agent_service = AgentService(session)

    async def _ensure_user_can_chat(self, current_user: User) -> None:
        if current_user.role == UserRole.AGENT.value:
            await self.agent_service.require_active_agent_access(current_user)

    async def start_or_get_private_chat(
        self,
        *,
        current_user: User,
        payload: ChatCreateRequest,
    ) -> tuple[Chat, Message | None]:
        if not current_user.is_email_verified:
            raise ForbiddenError("Email verification required")
        await self._ensure_user_can_chat(current_user)

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
        if not await self.agent_service.can_agent_use_features(agent):
            raise ForbiddenError("This agent does not currently have active platform access")

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

        chat = await self.chats.get_private_chat_between(
            user_a_id=current_user.id,
            user_b_id=target_user_id,
            property_id=payload.property_id,
        )
        created_message: Message | None = None
        if not chat:
            chat = Chat(
                chat_type=ChatType.PRIVATE.value,
                property_id=payload.property_id,
                created_by_id=current_user.id,
                target_user_id=target_user_id,
                underlying_agent_id=agent.id,
                routed_through_noxer=routed_through_noxer,
                visible_contact_type=visible_contact_type,
                title=property_obj.title if property_obj else None,
                is_active=True,
                last_message_at=None,
            )
            await self.chats.add_chat(chat)
            now = now_utc()
            await self.chats.add_participant(
                ChatParticipant(
                    chat_id=chat.id,
                    user_id=current_user.id,
                    role=ChatParticipantRole.MEMBER.value,
                    joined_at=now,
                )
            )
            await self.chats.add_participant(
                ChatParticipant(
                    chat_id=chat.id,
                    user_id=target_user_id,
                    role=ChatParticipantRole.MEMBER.value,
                    joined_at=now,
                )
            )
        if payload.initial_message:
            created_message = await self._create_message(
                chat=chat,
                sender=current_user,
                content=payload.initial_message,
                message_type=MessageType.TEXT,
            )
        await self.session.commit()
        loaded_chat = await self.chats.get_chat_by_id(chat.id)
        if not loaded_chat:
            raise NotFoundError("Chat not found after creation")
        if created_message:
            await self.session.refresh(created_message, attribute_names=["sender", "shared_property"])
        return loaded_chat, created_message

    async def create_group_chat(self, *, current_user: User, payload: GroupChatCreateRequest) -> Chat:
        await self.agent_service.require_active_agent_access(current_user)
        chat = Chat(
            chat_type=ChatType.GROUP.value,
            created_by_id=current_user.id,
            target_user_id=None,
            underlying_agent_id=None,
            routed_through_noxer=False,
            visible_contact_type=VisibleContactType.AGENT.value,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            country=payload.country.strip(),
            state=payload.state.strip(),
            local_government=payload.local_government.strip() if payload.local_government else None,
            community=payload.community.strip() if payload.community else None,
            is_active=True,
        )
        await self.chats.add_chat(chat)
        await self.chats.add_participant(
            ChatParticipant(
                chat_id=chat.id,
                user_id=current_user.id,
                role=ChatParticipantRole.OWNER.value,
                joined_at=now_utc(),
            )
        )
        await self.session.commit()
        loaded_chat = await self.chats.get_chat_by_id(chat.id)
        if not loaded_chat:
            raise NotFoundError("Group chat not found after creation")
        return loaded_chat

    async def discover_group_chats(
        self,
        *,
        current_user: User,
        page: int = 1,
        limit: int = 20,
        country: str | None = None,
        state: str | None = None,
        local_government: str | None = None,
        community: str | None = None,
    ) -> tuple[list[GroupChatListItem], int]:
        await self.agent_service.require_active_agent_access(current_user)
        chats, total = await self.chats.list_group_chats(
            page=page,
            limit=limit,
            country=country,
            state=state,
            local_government=local_government,
            community=community,
        )
        items: list[GroupChatListItem] = []
        for chat in chats:
            participant = await self.chats.get_participant(chat_id=chat.id, user_id=current_user.id)
            items.append(
                GroupChatListItem(
                    **self._chat_response_dict(chat),
                    participant_count=await self.chats.count_active_participants(chat.id),
                    is_member=participant is not None,
                )
            )
        return items, total

    async def join_group_chat(self, *, chat_id: UUID, current_user: User) -> Chat:
        await self.agent_service.require_active_agent_access(current_user)
        chat = await self.chats.get_chat_by_id(chat_id)
        if not chat or chat.chat_type != ChatType.GROUP.value:
            raise NotFoundError("Group chat not found")
        if not chat.is_active:
            raise ForbiddenError("This group chat is inactive")
        participant = await self.chats.get_participant_any(chat_id=chat.id, user_id=current_user.id)
        if participant:
            if participant.left_at is None:
                return chat
            participant.left_at = None
            participant.joined_at = now_utc()
            if participant.role != ChatParticipantRole.OWNER.value:
                participant.role = ChatParticipantRole.MEMBER.value
        else:
            await self.chats.add_participant(
                ChatParticipant(
                    chat_id=chat.id,
                    user_id=current_user.id,
                    role=ChatParticipantRole.MEMBER.value,
                    joined_at=now_utc(),
                )
            )
        await self.session.commit()
        return await self._require_chat(chat.id)

    async def leave_group_chat(self, *, chat_id: UUID, current_user: User) -> None:
        await self.agent_service.require_active_agent_access(current_user)
        chat = await self._require_chat(chat_id)
        if chat.chat_type != ChatType.GROUP.value:
            raise BadRequestError("This endpoint is only for group chats")
        participant = await self.chats.get_participant(chat_id=chat.id, user_id=current_user.id)
        if not participant:
            raise ForbiddenError("You are not a member of this group chat")
        if participant.role == ChatParticipantRole.OWNER.value:
            raise BadRequestError("Group owner cannot leave the group without transferring ownership")
        participant.left_at = now_utc()
        await self.session.commit()

    async def share_listing_message(
        self,
        *,
        chat_id: UUID,
        current_user: User,
        property_id: UUID,
        caption: str | None = None,
        client_message_id: str | None = None,
    ) -> Message:
        agent = await self.agent_service.require_active_agent_access(current_user)
        chat = await self.get_chat_for_user(chat_id=chat_id, current_user=current_user)
        if chat.chat_type != ChatType.GROUP.value:
            raise BadRequestError("Listings can only be shared through this endpoint in group chats")
        property_obj = await self.properties.get_agent_owned_property(property_id, agent.id)
        if not property_obj:
            raise NotFoundError("Property listing not found or does not belong to this agent")
        if property_obj.deleted_at is not None or not property_obj.is_published or property_obj.status == PropertyStatus.HIDDEN.value:
            raise BadRequestError("Only active published listings can be shared")
        self._validate_listing_location(chat=chat, property_obj=property_obj)
        message = await self._create_message(
            chat=chat,
            sender=current_user,
            content=caption,
            message_type=MessageType.LISTING,
            client_message_id=client_message_id,
            shared_property_id=property_obj.id,
        )
        await self.session.commit()
        await self.session.refresh(message, attribute_names=["sender", "shared_property"])
        return message

    @staticmethod
    def _validate_listing_location(*, chat: Chat, property_obj: Property) -> None:
        checks = (
            ("country", chat.country, property_obj.country),
            ("state", chat.state, property_obj.state),
            ("local government", chat.local_government, property_obj.local_government),
            ("community", chat.community, property_obj.community),
        )
        for label, group_value, property_value in checks:
            if group_value and (not property_value or group_value.strip().casefold() != property_value.strip().casefold()):
                raise BadRequestError(f"Property {label} does not match this geographic group")

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

    async def list_my_chats(
        self,
        *,
        current_user: User,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[ChatListItem], int]:
        await self._ensure_user_can_chat(current_user)
        chats, total = await self.chats.list_user_chats(user_id=current_user.id, page=page, limit=limit)
        items: list[ChatListItem] = []
        for chat in chats:
            participant = await self.chats.get_participant(chat_id=chat.id, user_id=current_user.id)
            last_message = await self.chats.get_last_message(chat.id)
            unread_count = await self.chats.count_unread(
                chat_id=chat.id,
                user_id=current_user.id,
                last_read_at=participant.last_read_at if participant else None,
            )
            items.append(
                ChatListItem(
                    **self._chat_response_dict(chat),
                    last_message=MessageResponse.model_validate(last_message) if last_message else None,
                    unread_count=unread_count,
                )
            )
        return items, total

    def _chat_response_dict(self, chat: Chat) -> dict:
        return {
            "id": chat.id,
            "chat_type": chat.chat_type,
            "property_id": chat.property_id,
            "created_by_id": chat.created_by_id,
            "target_user_id": chat.target_user_id,
            "underlying_agent_id": chat.underlying_agent_id,
            "routed_through_noxer": chat.routed_through_noxer,
            "visible_contact_type": chat.visible_contact_type,
            "title": chat.title,
            "description": chat.description,
            "country": chat.country,
            "state": chat.state,
            "local_government": chat.local_government,
            "community": chat.community,
            "is_active": chat.is_active,
            "last_message_id": chat.last_message_id,
            "last_message_at": chat.last_message_at,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "participants": [ChatParticipantResponse.model_validate(p) for p in chat.participants],
            "property": PropertyChatSummary.model_validate(chat.property) if chat.property else None,
        }

    async def _require_chat(self, chat_id: UUID) -> Chat:
        chat = await self.chats.get_chat_by_id(chat_id)
        if not chat:
            raise NotFoundError("Chat not found")
        return chat

    async def get_chat_for_user(self, *, chat_id: UUID, current_user: User) -> Chat:
        await self._ensure_user_can_chat(current_user)
        participant = await self.chats.get_participant(chat_id=chat_id, user_id=current_user.id)
        if not participant:
            raise ForbiddenError("You are not a participant in this chat")
        chat = await self._require_chat(chat_id)
        if not chat.is_active:
            raise ForbiddenError("This chat is inactive")
        return chat

    async def list_messages(
        self,
        *,
        chat_id: UUID,
        current_user: User,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[Message], int]:
        await self.get_chat_for_user(chat_id=chat_id, current_user=current_user)
        return await self.chats.list_messages(chat_id=chat_id, page=page, limit=limit)

    async def send_text_message(
        self,
        *,
        chat_id: UUID,
        current_user: User,
        content: str,
        client_message_id: str | None = None,
    ) -> Message:
        chat = await self.get_chat_for_user(chat_id=chat_id, current_user=current_user)
        message = await self._create_message(
            chat=chat,
            sender=current_user,
            content=content,
            message_type=MessageType.TEXT,
            client_message_id=client_message_id,
        )
        await self.session.commit()
        await self.session.refresh(message, attribute_names=["sender", "shared_property"])
        return message

    async def upload_media_message(
        self,
        *,
        chat_id: UUID,
        current_user: User,
        file: UploadFile,
        content: str | None = None,
        client_message_id: str | None = None,
    ) -> Message:
        chat = await self.get_chat_for_user(chat_id=chat_id, current_user=current_user)
        extension = Path(file.filename or "").suffix.lower()
        storage_path = f"chats/{chat_id}/{uuid.uuid4()}{extension}"
        uploaded = await SupabaseStorageService().upload_public_media(
            file=file,
            path=storage_path,
            allowed_media_types={MediaType.IMAGE, MediaType.VIDEO},
            max_image_size_bytes=settings.MAX_CHAT_IMAGE_SIZE_MB * 1024 * 1024,
            max_video_size_bytes=settings.MAX_CHAT_VIDEO_SIZE_MB * 1024 * 1024,
        )
        message_type = MessageType.IMAGE if uploaded.media_type == MediaType.IMAGE else MessageType.VIDEO
        message = await self._create_message(
            chat=chat,
            sender=current_user,
            content=content,
            message_type=message_type,
            media_url=uploaded.public_url,
            media_path=uploaded.path,
            media_content_type=uploaded.content_type,
            media_size_bytes=uploaded.size_bytes,
            client_message_id=client_message_id,
        )
        await self.session.commit()
        await self.session.refresh(message, attribute_names=["sender", "shared_property"])
        return message

    async def mark_chat_read(self, *, chat_id: UUID, current_user: User):
        await self._ensure_user_can_chat(current_user)
        participant = await self.chats.get_participant(chat_id=chat_id, user_id=current_user.id)
        if not participant:
            raise ForbiddenError("You are not a participant in this chat")
        read_at = now_utc()
        await self.chats.mark_read(participant=participant, read_at=read_at)
        await self.session.commit()
        return read_at

    async def _create_message(
        self,
        *,
        chat: Chat,
        sender: User,
        content: str | None,
        message_type: MessageType,
        media_url: str | None = None,
        media_path: str | None = None,
        media_content_type: str | None = None,
        media_size_bytes: int | None = None,
        client_message_id: str | None = None,
        shared_property_id: UUID | None = None,
    ) -> Message:
        if message_type == MessageType.TEXT and not (content and content.strip()):
            raise BadRequestError("Text message content is required")
        if message_type == MessageType.LISTING and not shared_property_id:
            raise BadRequestError("Listing messages require a property")
        message = Message(
            chat_id=chat.id,
            sender_id=sender.id,
            content=content.strip() if content else None,
            message_type=message_type.value,
            media_url=media_url,
            media_path=media_path,
            media_content_type=media_content_type,
            media_size_bytes=media_size_bytes,
            client_message_id=client_message_id,
            shared_property_id=shared_property_id,
        )
        await self.chats.add_message(message)
        chat.last_message_id = message.id
        chat.last_message_at = message.created_at or now_utc()
        return message
