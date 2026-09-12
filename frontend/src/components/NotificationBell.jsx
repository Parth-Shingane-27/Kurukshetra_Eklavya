import { useCallback, useEffect, useRef, useState } from "react";
import { getUnreadNotificationCount, listNotifications, markNotificationRead } from "../api/client";

// In-app Notification Center — real events only (grievance created/resolved, reminders the
// citizen explicitly set up). No push/email — this is purely an in-app feed, refreshed on
// open and on a light poll interval, matching what the backend actually delivers.
export default function NotificationBell({ citizenId }) {
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef(null);

  const refreshCount = useCallback(() => {
    if (!citizenId) return;
    getUnreadNotificationCount(citizenId)
      .then((r) => setUnreadCount(r.unread_count))
      .catch(() => {});
  }, [citizenId]);

  useEffect(() => {
    refreshCount();
    const interval = setInterval(refreshCount, 60000);
    return () => clearInterval(interval);
  }, [refreshCount]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function togglePanel() {
    const next = !open;
    setOpen(next);
    if (next && citizenId) {
      setLoading(true);
      try {
        const data = await listNotifications(citizenId);
        setNotifications(data);
      } finally {
        setLoading(false);
      }
    }
  }

  async function handleMarkRead(id) {
    try {
      await markNotificationRead(citizenId, id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      refreshCount();
    } catch {
      /* reminder-derived notifications reject mark-read — nothing to do */
    }
  }

  if (!citizenId) return null;

  return (
    <div className="notification-bell" ref={containerRef}>
      <button type="button" className="ghost small notification-bell-button" onClick={togglePanel} aria-label="Notifications">
        🔔 {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
      </button>
      {open && (
        <div className="notification-panel">
          {loading && <p className="hint">Loading…</p>}
          {!loading && notifications.length === 0 && <p className="hint">No notifications yet.</p>}
          {notifications.map((n) => (
            <div key={n.id} className={`notification-item ${n.read ? "" : "unread"}`}>
              <p>{n.message}</p>
              <div className="notification-item-footer">
                <span className="hint">{new Date(n.created_at).toLocaleString()}</span>
                {!n.read && (
                  <button type="button" className="ghost small" onClick={() => handleMarkRead(n.id)}>
                    Mark read
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
