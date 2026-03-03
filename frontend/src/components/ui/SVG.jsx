import icons from "@/config/icons";

export default function SVG({
  name,
  d,
  size = 18,
  color = "currentColor",
  fill = "none",
  style,
}) {
  const paths = d || icons[name];
  if (!paths) return null;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill}
      stroke={color}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0, ...style }}
    >
      {Array.isArray(paths) ? (
        paths.map((p, i) => <path key={i} d={p} />)
      ) : (
        <path d={paths} />
      )}
    </svg>
  );
}
