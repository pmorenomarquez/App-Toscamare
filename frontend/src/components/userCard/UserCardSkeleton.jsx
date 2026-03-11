const UserCardSkeleton = ({ index }) => {
  return (
    <div
      className="user-card"
      style={{ pointerEvents: "none", animationDelay: `${index * 0.05}s` }}
    >
      <div className="card-header">
        <div className="card-user-info">
          <div className="skeleton skeleton-avatar"></div>
          <div>
            <div className="skeleton skeleton-text-title"></div>
            <div className="skeleton skeleton-text-subtitle"></div>
          </div>
        </div>
      </div>
      <div className="card-footer">
        <div className="skeleton skeleton-badge"></div>
        <div className="skeleton skeleton-date"></div>
      </div>
    </div>
  );
};

export default UserCardSkeleton;
