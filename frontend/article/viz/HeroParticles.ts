import * as THREE from 'three';

export class HeroParticles {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private points: THREE.Points;
  private targetPositions: Float32Array;
  private startPositions: Float32Array;
  private startTime = performance.now();
  private rafHandle = 0;
  private container: HTMLElement;
  private positions: Float32Array;

  constructor(container: HTMLElement, count: number = 4000) {
    this.container = container;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.setClearColor(0x000000, 0);
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(
      45, container.clientWidth / container.clientHeight, 0.1, 100,
    );
    this.camera.position.set(0, 0, 6);

    this.positions = new Float32Array(count * 3);
    this.startPositions = new Float32Array(count * 3);
    this.targetPositions = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      // Random start: scattered across a sphere of radius 8
      const r = 8 * Math.cbrt(Math.random());
      const phi = Math.acos(2 * Math.random() - 1);
      const theta = 2 * Math.PI * Math.random();
      const sx = r * Math.sin(phi) * Math.cos(theta);
      const sy = r * Math.sin(phi) * Math.sin(theta);
      const sz = r * Math.cos(phi);
      this.startPositions[i * 3] = sx;
      this.startPositions[i * 3 + 1] = sy;
      this.startPositions[i * 3 + 2] = sz;
      // Target: a 4×5 grid of card slots
      const col = i % 5;
      const row = Math.floor((i / 5) % 4);
      this.targetPositions[i * 3] = (col - 2) * 1.0 + (Math.random() - 0.5) * 0.2;
      this.targetPositions[i * 3 + 1] = (1.5 - row) * 0.9 + (Math.random() - 0.5) * 0.15;
      this.targetPositions[i * 3 + 2] = (Math.random() - 0.5) * 0.3;
      this.positions[i * 3] = sx;
      this.positions[i * 3 + 1] = sy;
      this.positions[i * 3 + 2] = sz;
    }

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(this.positions, 3));
    const mat = new THREE.PointsMaterial({
      color: 0xff3d8a, size: 0.03, transparent: true, opacity: 0.85,
    });
    this.points = new THREE.Points(geom, mat);
    this.scene.add(this.points);

    this.startTime = performance.now();
    this.loop();
  }

  private loop = () => {
    const elapsed = (performance.now() - this.startTime) / 1000;
    const t = Math.min(1, elapsed / 4.0);
    const eased = 1 - Math.pow(1 - t, 3);
    const count = this.positions.length / 3;
    for (let i = 0; i < count; i++) {
      const k = i * 3;
      this.positions[k] = this.startPositions[k] * (1 - eased) + this.targetPositions[k] * eased;
      this.positions[k + 1] = this.startPositions[k + 1] * (1 - eased) + this.targetPositions[k + 1] * eased;
      this.positions[k + 2] = this.startPositions[k + 2] * (1 - eased) + this.targetPositions[k + 2] * eased;
    }
    (this.points.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    this.renderer.render(this.scene, this.camera);
    this.rafHandle = requestAnimationFrame(this.loop);
  };

  dispose(): void {
    cancelAnimationFrame(this.rafHandle);
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
