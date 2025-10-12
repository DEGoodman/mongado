"use client";

interface AIButtonProps {
  onClick: () => void;
}

export default function AIButton({ onClick }: AIButtonProps) {
  return (
    <button
      onClick={onClick}
      className="fixed right-6 bottom-6 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-110 z-40 flex items-center justify-center"
      aria-label="Open AI Assistant"
    >
      <svg
        className="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
        />
      </svg>
    </button>
  );
}
