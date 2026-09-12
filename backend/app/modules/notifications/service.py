"""Notification Center — see app/models/notification.py for the "in-app feed only, real
events only" boundary this module enforces."""

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["citizen_id"] = str(doc["citizen_id"])
    return doc


def _reminder_as_notification(reminder: dict) -> dict:
    """Reshapes an existing `reminders` document (Section 34's Deadline/Reminder agent) into
    the same notification shape — reuses real, already-computed data rather than duplicating
    it into a second collection."""
    if reminder.get("deadline_verified") and reminder.get("deadline_text"):
        message = f"Deadline reminder: {reminder['deadline_text']}"
    else:
        message = reminder.get("notification_reason") or "A reminder was set up for one of your schemes."
    return {
        "id": f"reminder:{reminder['_id']}",
        "citizen_id": str(reminder["citizen_id"]),
        "type": "deadline_reminder",
        "message": message,
        "related_id": str(reminder.get("scheme_id")) if reminder.get("scheme_id") else None,
        "read": True,  # reminders have no read/unread state of their own; never shown as "new"
        "created_at": reminder["created_at"],
    }


async def create_notification(
    db: AsyncIOMotorDatabase, citizen_id: str, notif_type: str, message: str, related_id: str | None = None
) -> dict:
    doc = {
        "citizen_id": ObjectId(citizen_id),
        "type": notif_type,
        "message": message,
        "related_id": related_id,
        "read": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.notifications.insert_one(doc)
    created = await db.notifications.find_one({"_id": result.inserted_id})
    return _serialize(created)


async def list_notifications(db: AsyncIOMotorDatabase, citizen_id: str) -> list[dict]:
    try:
        citizen_oid = ObjectId(citizen_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Profile not found")

    own = [_serialize(doc) async for doc in db.notifications.find({"citizen_id": citizen_oid})]
    reminders = [
        _reminder_as_notification(doc) async for doc in db.reminders.find({"citizen_id": citizen_oid})
    ]
    combined = own + reminders
    combined.sort(key=lambda n: n["created_at"], reverse=True)
    return combined


async def mark_read(db: AsyncIOMotorDatabase, citizen_id: str, notification_id: str) -> dict:
    if notification_id.startswith("reminder:"):
        raise HTTPException(status_code=400, detail="Reminder-derived notifications have no read state to change.")
    try:
        oid = ObjectId(notification_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Notification not found")
    doc = await db.notifications.find_one({"_id": oid, "citizen_id": ObjectId(citizen_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.notifications.update_one({"_id": oid}, {"$set": {"read": True}})
    updated = await db.notifications.find_one({"_id": oid})
    return _serialize(updated)


async def unread_count(db: AsyncIOMotorDatabase, citizen_id: str) -> int:
    try:
        citizen_oid = ObjectId(citizen_id)
    except (InvalidId, TypeError):
        return 0
    return await db.notifications.count_documents({"citizen_id": citizen_oid, "read": False})
