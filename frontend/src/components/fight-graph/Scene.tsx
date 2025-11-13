"use client";

import { Fragment, useMemo } from "react";
import { Canvas, type ThreeEvent } from "@react-three/fiber";
import {
  OrthographicCamera,
  PerspectiveCamera,
  OrbitControls,
  PerformanceMonitor,
} from "@react-three/drei";

import type {
  FightLayoutLinkPosition,
  FightLayoutNodePosition,
} from "../../types/fight-graph";
import { useFightGraphView } from "./ViewContext";

/**
 * Props consumed by the declarative Three.js scene responsible for rendering
 * the fight network. The component remains intentionally stateless so it can be
 * reused in Storybook or embedded in performance experiments.
 */
export interface FightGraphSceneProps {
  nodes: FightLayoutNodePosition[];
  links: FightLayoutLinkPosition[];
  nodeColorMap?: Map<string, string> | null;
  palette?: Map<string, string> | null;
  selectedNodeId?: string | null;
  hoveredNodeId?: string | null;
  defaultColor?: string;
  onNodeHover?: (nodeId: string | null, event?: ThreeEvent<PointerEvent>) => void;
  onNodeSelect?: (nodeId: string | null) => void;
  onPerformanceDrop?: () => void;
  onPerformanceRecover?: () => void;
}

const DEFAULT_NODE_COLOR = "#f1f5f9";

function resolveColor(
  node: FightLayoutNodePosition,
  nodeColorMap: Map<string, string> | null | undefined,
  palette: Map<string, string> | null | undefined,
  fallback: string,
): string {
  if (nodeColorMap?.has(node.fighter_id ?? node.id)) {
    return nodeColorMap.get(node.fighter_id ?? node.id) ?? fallback;
  }
  if (node.division && palette?.has(node.division)) {
    return palette.get(node.division) ?? fallback;
  }
  return fallback;
}

function Nodes({
  nodes,
  nodeColorMap,
  palette,
  selectedNodeId,
  hoveredNodeId,
  defaultColor,
  onHover,
  onSelect,
  depthFactor,
}: {
  nodes: FightLayoutNodePosition[];
  nodeColorMap?: Map<string, string> | null;
  palette?: Map<string, string> | null;
  selectedNodeId?: string | null;
  hoveredNodeId?: string | null;
  defaultColor: string;
  onHover?: (nodeId: string | null, event?: ThreeEvent<PointerEvent>) => void;
  onSelect?: (nodeId: string | null) => void;
  depthFactor: number;
}) {
  const maxDegree = useMemo(() => {
    return nodes.reduce((max, node) => Math.max(max, node.degree), 1);
  }, [nodes]);

  return (
    <group>
      {nodes.map((node) => {
        const isSelected = selectedNodeId === node.id;
        const isHovered = hoveredNodeId === node.id;
        const color = resolveColor(node, nodeColorMap ?? null, palette ?? null, defaultColor);
        const size = 0.8 + (node.degree / Math.max(1, maxDegree)) * 1.8;
        const emphasisScale = isSelected || isHovered ? 1.4 : 1;

        return (
          <mesh
            key={node.id}
            position={[node.x, node.y, node.z * depthFactor]}
            onPointerOver={(event) => {
              event.stopPropagation();
              onHover?.(node.id, event);
            }}
            onPointerOut={(event) => {
              event.stopPropagation();
              onHover?.(null, event);
            }}
            onClick={(event) => {
              event.stopPropagation();
              onSelect?.(isSelected ? null : node.id);
            }}
            scale={emphasisScale}
          >
            <sphereGeometry args={[size, 12, 12]} />
            <meshStandardMaterial color={color} emissive={isHovered ? color : "#000000"} emissiveIntensity={isHovered ? 0.4 : 0} />
          </mesh>
        );
      })}
    </group>
  );
}

function Edges({
  nodes,
  links,
  depthFactor,
}: {
  nodes: FightLayoutNodePosition[];
  links: FightLayoutLinkPosition[];
  depthFactor: number;
}) {
  const nodeMap = useMemo(() => {
    const map = new Map<string, FightLayoutNodePosition>();
    for (const node of nodes) {
      map.set(node.id, node);
    }
    return map;
  }, [nodes]);

  const segments = useMemo(() => {
    return links
      .map((link) => {
        const source = nodeMap.get(link.source);
        const target = nodeMap.get(link.target);
        if (!source || !target) {
          return null;
        }
        return (
          <line key={`${link.source}-${link.target}`}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                array={new Float32Array([
                  source.x,
                  source.y,
                  source.z * depthFactor,
                  target.x,
                  target.y,
                  target.z * depthFactor,
                ])}
                itemSize={3}
              />
            </bufferGeometry>
            <lineBasicMaterial color="#475569" transparent opacity={0.35} />
          </line>
        );
      })
      .filter(Boolean);
  }, [depthFactor, links, nodeMap]);

  return <Fragment>{segments}</Fragment>;
}

function FightGraphCameras(): JSX.Element {
  const { mode } = useFightGraphView();
  if (mode === "3d") {
    return (
      <PerspectiveCamera makeDefault position={[0, 0, 380]} fov={55} near={0.1} far={2000} />
    );
  }
  return (
    <OrthographicCamera makeDefault position={[0, 0, 500]} zoom={1.2} near={-1000} far={1000} />
  );
}

function FightGraphLights(): JSX.Element {
  return (
    <>
      <ambientLight intensity={0.65} />
      <spotLight position={[120, 260, 340]} angle={0.45} penumbra={0.5} intensity={1.2} castShadow />
      <spotLight position={[-150, -220, -320]} angle={0.35} penumbra={0.3} intensity={0.8} />
    </>
  );
}

export function FightGraphScene({
  nodes,
  links,
  nodeColorMap = null,
  palette = null,
  selectedNodeId,
  hoveredNodeId,
  defaultColor = DEFAULT_NODE_COLOR,
  onNodeHover,
  onNodeSelect,
  onPerformanceDrop,
  onPerformanceRecover,
}: FightGraphSceneProps) {
  const { depthFactor, mode } = useFightGraphView();

  return (
    <Canvas camera={{ position: [0, 0, 400] }} dpr={[1, 1.75]}>
      <color attach="background" args={["#020617"]} />
      <FightGraphCameras />
      <FightGraphLights />
      <PerformanceMonitor
        onDecline={() => onPerformanceDrop?.()}
        onIncline={() => onPerformanceRecover?.()}
        debounce={500}
      />
      <OrbitControls enableRotate={mode === "3d"} enableZoom enablePan minDistance={120} maxDistance={700} />
      <Edges nodes={nodes} links={links} depthFactor={depthFactor} />
      <Nodes
        nodes={nodes}
        nodeColorMap={nodeColorMap}
        palette={palette}
        selectedNodeId={selectedNodeId}
        hoveredNodeId={hoveredNodeId}
        defaultColor={defaultColor}
        onHover={onNodeHover}
        onSelect={onNodeSelect}
        depthFactor={depthFactor}
      />
    </Canvas>
  );
}
