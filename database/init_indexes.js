// Compound indexes per plan.md Section 13.
// Run with: mongosh <connection-string> database/init_indexes.js

db.eligibility_results.createIndex({ citizen_id: 1, scheme_id: 1 });
db.eligibility_results.createIndex({ citizen_id: 1, evaluated_at: 1 });

db.agent_audit_logs.createIndex({ citizen_id: 1, created_at: 1 });

db.bundles.createIndex({ citizen_id: 1 });

db.schemes.createIndex({ is_active: 1 });
db.schemes.createIndex({ category: 1 });

print("Indexes created.");
