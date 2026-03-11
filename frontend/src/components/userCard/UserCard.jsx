const UserCard = ({
  user,
  activeMenuId,
  isSelf,
  onAction,
  onMenuToggle,
  index,
}) => {
  const meta = ROLE_META[user.rol];

  return (
    <div
      className="user-card"
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r3)",
        padding: 24,
        position: "relative",
        zIndex: activeMenuId === user.id ? 9999 : 1,
        animationDelay: `${index * 0.05}s`,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div style={{ display: "flex", gap: 16 }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: "var(--r2)",
              background: meta.color + "15",
              border: `1px solid ${meta.color}30`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <SVG name="user" size={24} color={meta.color} />
          </div>
          <div>
            <div
              style={{
                fontWeight: 600,
                fontSize: 17,
                color: "var(--text-1)",
              }}
            >
              {user.nombre}
            </div>
            <div
              style={{
                fontSize: 13,
                color: "var(--text-3)",
                marginTop: 2,
              }}
            >
              {user.email}
            </div>
          </div>
        </div>

        <UserActions
          u={user}
          isSelf={isSelf}
          onAction={onAction}
          onMenuToggle={onMenuToggle}
        />
      </div>

      <div
        style={{
          marginTop: 24,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Badge color={meta.color}>{meta.label}</Badge>
        <div style={{ fontSize: 12, color: "var(--text-4)" }}>
          {formatDate(user.created_at)}
        </div>
      </div>
    </div>
  );
};

export default UserCard;
