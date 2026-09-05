import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type WheelEvent as ReactWheelEvent } from "react";
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react";
import { publicUrl } from "../lib/publicUrl";

type Props = {
  images: string[];
  startIndex?: number;
  alt: string;
  onClose: () => void;
};

const MIN_SCALE = 1;
const MAX_SCALE = 4;

export function ImageLightbox({ images, startIndex = 0, alt, onClose }: Props) {
  const [index, setIndex] = useState(startIndex);
  const [scale, setScale] = useState(1);
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const closeRef = useRef<HTMLButtonElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const pinchStart = useRef<{ dist: number; scale: number } | null>(null);
  const panStart = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const lastTap = useRef(0);

  const src = images[index] || images[0];
  const canPrev = images.length > 1;
  const resetView = useCallback(() => {
    setScale(1);
    setTx(0);
    setTy(0);
  }, []);

  useEffect(() => {
    resetView();
  }, [index, resetView]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && canPrev) setIndex((i) => (i - 1 + images.length) % images.length);
      if (e.key === "ArrowRight" && canPrev) setIndex((i) => (i + 1) % images.length);
      if (e.key === "+" || e.key === "=") setScale((s) => Math.min(MAX_SCALE, s + 0.25));
      if (e.key === "-") setScale((s) => Math.max(MIN_SCALE, s - 0.25));
      if (e.key !== "Tab" || !rootRef.current) return;
      const nodes = [...rootRef.current.querySelectorAll<HTMLElement>("button")].filter((el) => !el.hasAttribute("disabled"));
      if (!nodes.length) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose, canPrev, images.length]);

  const onWheel = (e: ReactWheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.15 : 0.15;
    setScale((s) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, s + delta)));
  };

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      pinchStart.current = { dist, scale };
      panStart.current = null;
    } else if (pointers.current.size === 1) {
      panStart.current = { x: e.clientX, y: e.clientY, tx, ty };
      const now = Date.now();
      if (now - lastTap.current < 280) {
        if (scale > 1.05) resetView();
        else setScale(2.2);
      }
      lastTap.current = now;
    }
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 2 && pinchStart.current) {
      const [a, b] = [...pointers.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      const next = pinchStart.current.scale * (dist / Math.max(1, pinchStart.current.dist));
      setScale(Math.min(MAX_SCALE, Math.max(MIN_SCALE, next)));
      return;
    }
    if (pointers.current.size === 1 && panStart.current && scale > 1.01) {
      const dx = e.clientX - panStart.current.x;
      const dy = e.clientY - panStart.current.y;
      setTx(panStart.current.tx + dx);
      setTy(panStart.current.ty + dy);
    }
  };

  const onPointerUp = (e: ReactPointerEvent<HTMLDivElement>) => {
    pointers.current.delete(e.pointerId);
    if (pointers.current.size < 2) pinchStart.current = null;
    if (pointers.current.size === 0) panStart.current = null;
  };

  // swipe between images when not zoomed
  const swipeX = useRef<number | null>(null);
  const onSwipeStart = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (scale > 1.05) return;
    swipeX.current = e.clientX;
  };
  const onSwipeEnd = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (swipeX.current == null || scale > 1.05 || !canPrev) {
      swipeX.current = null;
      return;
    }
    const dx = e.clientX - swipeX.current;
    swipeX.current = null;
    if (Math.abs(dx) < 50) return;
    if (dx < 0) setIndex((i) => (i + 1) % images.length);
    else setIndex((i) => (i - 1 + images.length) % images.length);
  };

  return (
    <div className="lightbox-root" role="dialog" aria-modal="true" aria-label="Просмотр фото" ref={rootRef}>
      <button type="button" className="lightbox-backdrop" aria-label="Закрыть" onClick={onClose} />
      <div className="lightbox-chrome">
        <button ref={closeRef} type="button" className="lightbox-close" aria-label="Закрыть" onClick={onClose}>
          <X size={22} />
        </button>
        <div className="lightbox-tools">
          <button type="button" aria-label="Уменьшить" onClick={() => setScale((s) => Math.max(MIN_SCALE, s - 0.35))}>
            <ZoomOut size={20} />
          </button>
          <button type="button" aria-label="Увеличить" onClick={() => setScale((s) => Math.min(MAX_SCALE, s + 0.35))}>
            <ZoomIn size={20} />
          </button>
        </div>
        {canPrev ? (
          <>
            <button
              type="button"
              className="lightbox-nav lightbox-prev"
              aria-label="Предыдущее фото"
              onClick={() => setIndex((i) => (i - 1 + images.length) % images.length)}
            >
              <ChevronLeft size={28} />
            </button>
            <button
              type="button"
              className="lightbox-nav lightbox-next"
              aria-label="Следующее фото"
              onClick={() => setIndex((i) => (i + 1) % images.length)}
            >
              <ChevronRight size={28} />
            </button>
          </>
        ) : null}
        <p className="lightbox-counter">
          {index + 1} / {images.length}
        </p>
      </div>
      <div
        className="lightbox-stage"
        ref={stageRef}
        onWheel={onWheel}
        onPointerDown={(e) => {
          onSwipeStart(e);
          onPointerDown(e);
        }}
        onPointerMove={onPointerMove}
        onPointerUp={(e) => {
          onSwipeEnd(e);
          onPointerUp(e);
        }}
        onPointerCancel={onPointerUp}
      >
        {src ? (
          <img
            className="lightbox-img"
            src={publicUrl(src)}
            alt={alt}
            draggable={false}
            style={{ transform: `translate3d(${tx}px, ${ty}px, 0) scale(${scale})` }}
          />
        ) : null}
        {/* preload neighbors */}
        {images.map((path, i) =>
          Math.abs(i - index) === 1 ? (
            <link key={path} rel="preload" as="image" href={publicUrl(path)} />
          ) : null,
        )}
      </div>
    </div>
  );
}
