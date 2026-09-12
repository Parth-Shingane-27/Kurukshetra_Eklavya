from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_platform_analytics(db: AsyncIOMotorDatabase) -> dict:
    total_citizens = await db.citizens.count_documents({})
    total_active_schemes = await db.schemes.count_documents({"is_active": True})
    total_eligibility_evaluations = await db.eligibility_results.count_documents({})
    total_bundles_generated = await db.bundles.count_documents({})
    open_grievances = await db.grievances.count_documents({"status": "open"})
    resolved_grievances = await db.grievances.count_documents({"status": "resolved"})
    fraud_flags_pending_review = await db.fraud_flags.count_documents({"reviewed": False})
    fraud_flags_reviewed = await db.fraud_flags.count_documents({"reviewed": True})
    rag_candidates_pending = await db.rag_candidate_updates.count_documents({"status": "pending"})

    category_pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    schemes_by_category = [
        {"category": doc["_id"], "count": doc["count"]}
        async for doc in db.schemes.aggregate(category_pipeline)
    ]

    save_pipeline = [
        {"$group": {"_id": "$scheme_id", "save_count": {"$sum": 1}}},
        {"$sort": {"save_count": -1}},
        {"$limit": 10},
    ]
    most_saved_raw = [doc async for doc in db.saved_schemes.aggregate(save_pipeline)]
    scheme_ids = [doc["_id"] for doc in most_saved_raw]
    schemes_by_id = {s["_id"]: s async for s in db.schemes.find({"_id": {"$in": scheme_ids}})} if scheme_ids else {}
    most_saved_schemes = [
        {
            "scheme_id": str(doc["_id"]),
            "scheme_name": schemes_by_id[doc["_id"]]["name"] if doc["_id"] in schemes_by_id else "(deleted scheme)",
            "save_count": doc["save_count"],
        }
        for doc in most_saved_raw
    ]

    return {
        "total_citizens": total_citizens,
        "total_active_schemes": total_active_schemes,
        "total_eligibility_evaluations": total_eligibility_evaluations,
        "total_bundles_generated": total_bundles_generated,
        "open_grievances": open_grievances,
        "resolved_grievances": resolved_grievances,
        "fraud_flags_pending_review": fraud_flags_pending_review,
        "fraud_flags_reviewed": fraud_flags_reviewed,
        "rag_candidates_pending": rag_candidates_pending,
        "schemes_by_category": schemes_by_category,
        "most_saved_schemes": most_saved_schemes,
    }
