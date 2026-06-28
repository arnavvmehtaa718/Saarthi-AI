import React from "react";

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

export default function GlassCard({ children, className = "", ...props }: GlassCardProps) {
  return (
    <div
      className={`glass-card rounded-[var(--radius)] p-6 transition-all duration-300 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
