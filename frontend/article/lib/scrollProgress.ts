import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

let lenis: Lenis | null = null;

export function initSmoothScroll(): () => void {
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced) return () => undefined;
  lenis = new Lenis({ smoothWheel: true, lerp: 0.1 });
  const raf = (t: number) => {
    lenis?.raf(t);
    requestAnimationFrame(raf);
  };
  requestAnimationFrame(raf);
  lenis.on('scroll', ScrollTrigger.update);
  return () => {
    lenis?.destroy();
    lenis = null;
  };
}

export interface ScrubOptions {
  start?: string;
  end?: string;
  pin?: boolean;
}

export function scrollScrub(
  triggerEl: Element,
  onUpdate: (t: number) => void,
  opts: ScrubOptions = {},
): () => void {
  const trigger = ScrollTrigger.create({
    trigger: triggerEl,
    start: opts.start ?? 'top top',
    end: opts.end ?? 'bottom top',
    scrub: true,
    pin: opts.pin ?? false,
    onUpdate: (self) => onUpdate(self.progress),
  });
  return () => trigger.kill();
}

export function clamp(x: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, x));
}

export function mapRange(
  x: number, inLo: number, inHi: number, outLo: number, outHi: number,
): number {
  const t = clamp((x - inLo) / (inHi - inLo), 0, 1);
  return outLo + t * (outHi - outLo);
}
