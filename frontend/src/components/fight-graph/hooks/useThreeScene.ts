import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import type { FightGraphResponse } from "@/types/fight-graph";

export type FightGraphViewMode = "3d" | "2d";

interface UseThreeSceneOptions {
  /** Controls whether the scene should be rendered in 3D or flattened to 2D. */
  mode: FightGraphViewMode;
}

/**
 * Utility hook that bootstraps a reusable Three.js scene for rendering
 * the fight graph. All imperative WebGL lifecycle management is handled
 * here so React components can remain declarative.
 */
export function useThreeScene(
  containerRef: React.RefObject<HTMLDivElement>,
  graph: FightGraphResponse | null,
  { mode }: UseThreeSceneOptions,
) {
  const requestRef = useRef<number>();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    // --- Scene bootstrap ----------------------------------------------------
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x05070f);
    scene.fog = new THREE.FogExp2(0x05070f, 0.0125);

    const camera = new THREE.PerspectiveCamera(
      60,
      container.clientWidth / Math.max(container.clientHeight, 1),
      0.1,
      1000,
    );
    camera.position.set(0, 60, 160);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight, false);
    renderer.shadowMap.enabled = false;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enablePan = true;
    controls.minDistance = 40;
    controls.maxDistance = 400;

    // Soft ambient and key lighting provide subtle depth cues.
    const ambientLight = new THREE.AmbientLight(0x5c6bc0, 0.8);
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.6);
    keyLight.position.set(60, 120, 80);
    scene.add(ambientLight, keyLight);

    const nodesGroup = new THREE.Group();
    nodesGroup.name = "fight-graph-nodes";
    const linksGroup = new THREE.Group();
    linksGroup.name = "fight-graph-links";
    scene.add(nodesGroup, linksGroup);

    /**
     * Helper that disposes of every geometry and material to prevent
     * GPU memory leaks when React tears down the scene.
     */
    const disposeGroup = (group: THREE.Group) => {
      group.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
          object.geometry?.dispose();
          const material = object.material;
          if (Array.isArray(material)) {
            material.forEach((entry) => entry.dispose());
          } else if (material) {
            material.dispose();
          }
        }
      });
      group.clear();
    };

    // --- Layout calculation -------------------------------------------------
    if (graph && graph.nodes.length > 0) {
      const nodeMaterial = new THREE.MeshPhongMaterial({
        color: new THREE.Color(0x66d9ef),
        emissive: new THREE.Color(0x0f1629),
        shininess: 80,
      });
      const highlightMaterial = new THREE.MeshPhongMaterial({
        color: new THREE.Color(0xf92672),
        emissive: new THREE.Color(0x31113d),
        shininess: 100,
      });
      const linkMaterial = new THREE.LineBasicMaterial({
        color: 0x24334f,
        opacity: 0.55,
        transparent: true,
      });

      const radius = 60;
      const nodePositions = new Map<string, THREE.Vector3>();

      graph.nodes.forEach((node, index) => {
        const theta = index * ((Math.PI * (3 - Math.sqrt(5))) as number);
        const y = 1 - (index / Math.max(graph.nodes.length - 1, 1)) * 2;
        const radialDistance = Math.sqrt(1 - y * y);
        const position = new THREE.Vector3(
          Math.cos(theta) * radialDistance * radius,
          mode === "3d" ? y * radius : 0,
          Math.sin(theta) * radialDistance * radius,
        );

        nodePositions.set(node.fighter_id, position);

        const geometry = new THREE.SphereGeometry(2.4, 24, 24);
        const mesh = new THREE.Mesh(
          geometry,
          node.total_fights > 10 ? highlightMaterial : nodeMaterial,
        );
        mesh.position.copy(position);
        mesh.userData = node;
        nodesGroup.add(mesh);
      });

      graph.links.forEach((link) => {
        const source = nodePositions.get(link.source);
        const target = nodePositions.get(link.target);
        if (!source || !target) {
          return;
        }
        const points = new Float32Array([
          source.x,
          source.y,
          source.z,
          target.x,
          target.y,
          target.z,
        ]);
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(points, 3));
        const line = new THREE.Line(geometry, linkMaterial);
        line.userData = link;
        linksGroup.add(line);
      });
    }

    // --- Animation loop -----------------------------------------------------
    const animate = () => {
      controls.update();
      renderer.render(scene, camera);
      requestRef.current = requestAnimationFrame(animate);
    };
    animate();

    const handleResize = () => {
      if (!container) {
        return;
      }
      const { clientWidth, clientHeight } = container;
      camera.aspect = clientWidth / Math.max(clientHeight, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(clientWidth, clientHeight, false);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
      disposeGroup(nodesGroup);
      disposeGroup(linksGroup);
      controls.dispose();
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, [containerRef, graph, mode]);
}
