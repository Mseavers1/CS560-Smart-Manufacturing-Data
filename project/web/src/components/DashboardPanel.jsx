export default function DashboardPanel({ children, className = "" }) {
    return (
        <div
            className={`min-h-[280px] overflow-hidden rounded-xl border border-gray-200 bg-white p-4 shadow-sm ${className}`}
        >
            {children}
        </div>
    );
}