export function ChartIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      height="1em"
      viewBox="0 0 24 24"
      width="1em"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      >
        <path d="M9 5v4" />
        <rect height="6" rx="1" width="4" x="7" y="9" />
        <path d="M9 15v2m8-14v2" />
        <rect height="8" rx="1" width="4" x="15" y="5" />
        <path d="M17 13v3M3 3v16a2 2 0 0 0 2 2h16" />
      </g>
    </svg>
  );
}
