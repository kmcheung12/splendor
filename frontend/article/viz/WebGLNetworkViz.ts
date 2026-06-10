import * as THREE from 'three';
import type { NetworkVisualization } from './NetworkVisualization';
import type { LayerActivations, NetworkSpec } from './types';

const MAX_VISIBLE = 24;

export class WebGLNetworkViz implements NetworkVisualization {
  private renderer: THREE.WebGLRenderer | null = null;
  private scene: THREE.Scene | null = null;
  private camera: THREE.PerspectiveCamera | null = null;
  private container: HTMLElement | null = null;
  private network: NetworkSpec | null = null;
  private rafHandle = 0;
  private nodeMeshes: THREE.InstancedMesh[] = [];
  private edgeLines: THREE.LineSegments[] = [];
  private scrollT = 0;

  mount(container: HTMLElement, network: NetworkSpec): void {
    this.container = container;
    this.network = network;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true, alpha: true, powerPreference: 'high-performance',
      });
    } catch {
      throw new Error('WebGL unavailable');
    }
    if (!renderer.getContext()) {
      throw new Error('WebGL context not created');
    }
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x0a0d12, 0);
    container.appendChild(renderer.domElement);
    this.renderer = renderer;

    const aspect = container.clientWidth / container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100);
    this.camera.position.set(0, 0, 8);

    this.scene = new THREE.Scene();
    this.buildLayers();
    this.startLoop();
  }

  setActivations(_obs: Float32Array, _layerOutputs: LayerActivations): void {
    // Plan 5 wires activations to instance colours.
  }

  setScrollProgress(t: number): void {
    this.scrollT = t;
    if (!this.camera) return;
    this.camera.position.x = (t - 0.5) * 6;
    this.camera.lookAt(0, 0, 0);
  }

  setHighlightedAction(_actionIdx: number | null): void {
    // Plan 5 wires this.
  }

  dispose(): void {
    cancelAnimationFrame(this.rafHandle);
    this.nodeMeshes.forEach((m) => m.dispose());
    this.edgeLines.forEach((l) => l.geometry.dispose());
    this.renderer?.dispose();
    this.renderer?.domElement.remove();
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.nodeMeshes = [];
    this.edgeLines = [];
  }

  private buildLayers(): void {
    if (!this.network || !this.scene) return;
    const layerSizes = [
      this.network.inputSize,
      ...this.network.hiddenLayers,
      this.network.outputSize,
    ];
    const spacing = 1.5;
    const xs = layerSizes.map((_, i) =>
      (i - (layerSizes.length - 1) / 2) * spacing,
    );
    const sphere = new THREE.SphereGeometry(0.05, 12, 12);
    const material = new THREE.MeshBasicMaterial({ color: 0xff3d8a });

    layerSizes.forEach((size, li) => {
      const visible = Math.min(size, MAX_VISIBLE);
      const mesh = new THREE.InstancedMesh(sphere, material, visible);
      const dummy = new THREE.Object3D();
      const yStep = visible > 1 ? 3 / (visible - 1) : 0;
      for (let i = 0; i < visible; i++) {
        dummy.position.set(xs[li], 1.5 - i * yStep, 0);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);
      }
      this.scene!.add(mesh);
      this.nodeMeshes.push(mesh);
    });

    // Edges
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0xff3d8a, transparent: true, opacity: 0.08,
    });
    for (let i = 0; i < layerSizes.length - 1; i++) {
      const a = Math.min(layerSizes[i], MAX_VISIBLE);
      const b = Math.min(layerSizes[i + 1], MAX_VISIBLE);
      const positions: number[] = [];
      const yA = (k: number) => 1.5 - k * (a > 1 ? 3 / (a - 1) : 0);
      const yB = (k: number) => 1.5 - k * (b > 1 ? 3 / (b - 1) : 0);
      for (let ja = 0; ja < a; ja++) {
        for (let jb = 0; jb < b; jb++) {
          positions.push(xs[i], yA(ja), 0, xs[i + 1], yB(jb), 0);
        }
      }
      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position',
        new THREE.Float32BufferAttribute(positions, 3));
      const line = new THREE.LineSegments(geom, lineMaterial);
      this.scene!.add(line);
      this.edgeLines.push(line);
    }
  }

  private startLoop(): void {
    const tick = () => {
      if (!this.renderer || !this.scene || !this.camera) return;
      this.renderer.render(this.scene, this.camera);
      this.rafHandle = requestAnimationFrame(tick);
    };
    tick();
  }
}
