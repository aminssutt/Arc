/**
 * Demo-video slot for the landing.
 *
 * Pass a YouTube video id (the part after `watch?v=` or `youtu.be/`) and it
 * renders a responsive 16:9 privacy-friendly embed. Leave it empty and it shows
 * an on-brand placeholder — so the section can ship now and the real video drops
 * in with a one-line change (set `DEMO_VIDEO_ID` in `app/page.tsx`).
 */

interface VideoEmbedProps {
  /** YouTube video id, e.g. "dQw4w9WgXcQ". Empty string → placeholder. */
  youtubeId?: string;
  title?: string;
}

export function VideoEmbed({ youtubeId, title = "Arc — full demo" }: VideoEmbedProps) {
  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-card border border-surface-line bg-surface">
      {youtubeId ? (
        <iframe
          className="absolute inset-0 h-full w-full"
          src={`https://www.youtube-nocookie.com/embed/${youtubeId}?rel=0`}
          title={title}
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      ) : (
        <div
          className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-center"
          style={{ background: "radial-gradient(60% 60% at 50% 42%, rgba(0,120,174,0.20), transparent 70%)" }}
          role="img"
          aria-label="Demo video placeholder — the full Arc run will play here."
        >
          {/* faint grid for texture */}
          <span className="grid-lines-dark pointer-events-none absolute inset-0 opacity-40" aria-hidden />
          <span className="relative flex h-16 w-16 items-center justify-center rounded-full bg-[#0078AE] shadow-[0_0_44px_-6px_rgba(0,120,174,0.75)]">
            <svg viewBox="0 0 24 24" className="h-7 w-7 translate-x-[2px] fill-white" aria-hidden>
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
          <div className="relative">
            <p className="font-mono text-[11px] uppercase tracking-label text-paper/45">Demo video</p>
            <p className="mt-1 font-display text-lg text-paper">The full run — coming soon.</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default VideoEmbed;
