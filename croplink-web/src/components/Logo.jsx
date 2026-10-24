export default function Logo({ size = 28 }) {
  return (
    <span className="logo">
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <circle cx="16" cy="16" r="15" stroke="currentColor" strokeOpacity="0.35" />
        <path d="M16 25V14" stroke="#C8F169" strokeWidth="2" strokeLinecap="round" />
        <path d="M16 15c0-4.2-2.6-6.6-7-6.8 0 4.4 2.6 6.8 7 6.8Z" fill="#C8F169" />
        <path d="M16 18c0-3.4 2.2-5.6 6.4-5.8 0 3.8-2.2 5.8-6.4 5.8Z" fill="#C8F169" fillOpacity="0.7" />
      </svg>
      <span className="logo__word">CropLink</span>
    </span>
  );
}
