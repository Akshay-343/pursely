export const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="block space-y-1.5">
    <span className="text-sm font-medium leading-none">{label}</span>
    {children}
  </label>
);
