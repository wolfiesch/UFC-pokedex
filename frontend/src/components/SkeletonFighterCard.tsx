import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";

export default function SkeletonFighterCard() {
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="p-6 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              {/* Fighter name skeleton */}
              <div className="h-7 w-40 animate-pulse rounded bg-muted shimmer" />
              {/* Record badge skeleton */}
              <div className="h-5 w-16 animate-pulse rounded bg-muted shimmer" />
            </div>
            {/* Nickname skeleton */}
            <div className="h-4 w-32 animate-pulse rounded bg-muted/60 shimmer" />
          </div>
          {/* Favorite button skeleton */}
          <div className="h-9 w-20 animate-pulse rounded-md bg-muted shimmer" />
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col space-y-4">
        {/* Image placeholder skeleton */}
        <div className="flex justify-center">
          <div className="relative flex aspect-[3/4] w-40 animate-pulse items-center justify-center overflow-hidden rounded-2xl border border-border/60 bg-muted shimmer" />
        </div>

        {/* Stats grid skeleton */}
        <dl className="grid grid-cols-2 gap-3 text-sm">
          {[...Array(4)].map((_, i) => (
            <div key={i}>
              <div className="mb-1 h-3 w-16 animate-pulse rounded bg-muted/60 shimmer" />
              <div className="h-4 w-20 animate-pulse rounded bg-muted shimmer" />
            </div>
          ))}
        </dl>
      </CardContent>

      <CardFooter className="items-center justify-between pt-0">
        {/* Division badge skeleton */}
        <div className="h-6 w-28 animate-pulse rounded-full bg-muted shimmer" />
        {/* View arrow skeleton */}
        <div className="h-3 w-12 animate-pulse rounded bg-muted/60 shimmer" />
      </CardFooter>
    </Card>
  );
}
