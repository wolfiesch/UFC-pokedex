import { notFound } from "next/navigation";
import EventDetailPageClient from "@/components/events/EventDetailPageClient";
import { getAllEventIdsSSR } from "@/lib/api-ssr";

// Enable static params for export
export const dynamicParams = true;

type EventDetailPageProps = {
  params: {
    id?: string;
  };
};

/**
 * Generate static params for all events at build time
 */
export async function generateStaticParams() {
  try {
    const events = await getAllEventIdsSSR();
    const params = events.map(({ id }) => ({ id }));
    // For static export, ensure we have at least one param
    return params.length > 0 ? params : [{ id: "placeholder" }];
  } catch (error) {
    console.error("Failed to generate static params for events:", error);
    // For static export, return a placeholder to avoid build error
    return [{ id: "placeholder" }];
  }
}

export default function EventDetailPage({ params }: EventDetailPageProps) {
  const eventId = params?.id?.trim();

  if (!eventId) {
    notFound();
  }

  // Render client component with event ID
  return <EventDetailPageClient eventId={eventId} />;
}
