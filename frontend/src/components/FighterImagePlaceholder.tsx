import { memo } from "react";

import { cn, getColorFromString, getInitials } from "@/lib/utils";

type Props = {
  name: string;
  division?: string | null;
  className?: string;
};

function FighterImagePlaceholderComponent({
  name,
  division,
  className,
}: Props) {
  const initials = getInitials(name);
  const colorClasses = getColorFromString(name);

  return (
    <div className={cn(colorClasses, "text-white shadow-inner", className)}>
      <span className="text-3xl font-semibold tracking-tight drop-shadow">
        {initials || "??"}
      </span>
      {division ? (
        <span className="pointer-events-none absolute bottom-2 text-[0.55rem] uppercase tracking-[0.35em] text-white/75">
          {division}
        </span>
      ) : null}
    </div>
  );
}

FighterImagePlaceholderComponent.displayName = "FighterImagePlaceholder";

export default memo(FighterImagePlaceholderComponent);
