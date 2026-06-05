export const ARC_DURATION = 380

export function flyArc(
  fromRect: DOMRect,
  toRect: DOMRect,
  imgSrc: string,
  duration = ARC_DURATION,
  delay = 0,
  onComplete?: () => void,
  size = 28,
) {
  if (delay > 0) {
    setTimeout(() => flyArc(fromRect, toRect, imgSrc, duration, 0, onComplete, size), delay)
    return
  }

  const el = document.createElement('img')
  el.src = imgSrc
  el.draggable = false
  el.style.cssText = `
    position:fixed; width:${size}px; height:${size}px;
    pointer-events:none; z-index:9999;
    image-rendering:pixelated; transform-origin:center;
    left:0; top:0;
  `
  document.body.appendChild(el)

  const fromX = fromRect.left + fromRect.width  / 2 - size / 2
  const fromY = fromRect.top  + fromRect.height / 2 - size / 2
  const toX   = toRect.left   + toRect.width    / 2 - size / 2
  const toY   = toRect.top    + toRect.height   / 2 - size / 2

  const midX = (fromX + toX) / 2
  const dist = Math.hypot(toX - fromX, toY - fromY)
  const ctrlY = Math.min(fromY, toY) - Math.max(32, dist * 0.4)

  const start = performance.now()

  function step(now: number) {
    const raw = Math.min(1, (now - start) / duration)
    const t = raw < 0.5 ? 4 * raw ** 3 : 1 - (-2 * raw + 2) ** 3 / 2

    const u = 1 - t
    const x = u * u * fromX + 2 * u * t * midX + t * t * toX
    const y = u * u * fromY + 2 * u * t * ctrlY + t * t * toY
    const scale = 1 + 0.3 * Math.sin(t * Math.PI)

    el.style.transform = `translate(${x}px, ${y}px) scale(${scale})`

    if (raw < 1) {
      requestAnimationFrame(step)
    } else {
      el.remove()
      onComplete?.()
    }
  }

  requestAnimationFrame(step)
}
