// frontend/src/lib/animationQueue.ts

type AnimFn = () => Promise<void>

class AnimationQueue {
  private queue: AnimFn[] = []
  private running = false

  enqueue(fn: AnimFn): void {
    this.queue.push(fn)
    if (!this.running) this._drain()
  }

  private async _drain(): Promise<void> {
    this.running = true
    while (this.queue.length > 0) {
      const fn = this.queue.shift()!
      await fn()
    }
    this.running = false
  }
}

export const animQueue = new AnimationQueue()

export const delay = (ms: number) => new Promise<void>(r => setTimeout(r, ms))
