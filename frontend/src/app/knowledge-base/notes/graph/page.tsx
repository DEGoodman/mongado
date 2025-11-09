"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import SettingsDropdown from "@/components/SettingsDropdown";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

interface GraphNode {
  id: string;
  title: string;
  author: string;
  tags: string[];
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface GraphEdge {
  source: string;
  target: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  count: {
    nodes: number;
    edges: number;
  };
}

export default function NotesGraphPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    async function fetchGraphData() {
      try {
        setLoading(true);
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

        // Get auth token if available
        const token = localStorage.getItem("adminPasskey");
        const headers: HeadersInit = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(`${apiUrl}/api/notes/graph/data`, {
          headers,
          credentials: "include",
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch graph data: ${response.statusText}`);
        }

        const data: GraphData = await response.json();

        // Initialize node positions near center with some randomness
        const centerX = 600; // Half of canvas width (1200)
        const centerY = 350; // Half of canvas height (700)
        const spread = 200; // Initial spread radius

        data.nodes = data.nodes.map((node) => ({
          ...node,
          x: centerX + (Math.random() - 0.5) * spread,
          y: centerY + (Math.random() - 0.5) * spread,
          vx: 0,
          vy: 0,
        }));

        setGraphData(data);
        logger.info("Graph data loaded", {
          nodes: data.count.nodes,
          edges: data.count.edges,
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load graph";
        setError(message);
        logger.error("Failed to load graph data", err);
      } finally {
        setLoading(false);
      }
    }

    fetchGraphData();
  }, []);

  // Force-directed graph simulation
  useEffect(() => {
    if (!graphData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const nodes = graphData.nodes;
    const edges = graphData.edges;

    // Simulation parameters
    let alpha = 1.0; // Start high
    const alphaDecay = 0.02; // Cooling rate
    const alphaMin = 0.001; // Stop when alpha gets this low

    function animate() {
      if (!ctx) return;

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Only apply forces if simulation is still cooling
      if (alpha > alphaMin) {
        // Repulsion between all nodes (charge force)
        const chargeStrength = 3000; // Increased for better spacing
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const dx = nodes[j].x! - nodes[i].x!;
            const dy = nodes[j].y! - nodes[i].y!;
            const distSq = dx * dx + dy * dy;
            const dist = Math.sqrt(distSq) || 1;

            // Stronger repulsion at close range
            const force = (chargeStrength / distSq) * alpha;

            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            nodes[i].vx = nodes[i].vx! - fx;
            nodes[i].vy = nodes[i].vy! - fy;
            nodes[j].vx = nodes[j].vx! + fx;
            nodes[j].vy = nodes[j].vy! + fy;
          }
        }

        // Attraction along edges (spring force)
        const linkStrength = 0.3;
        const linkDistance = 100;
        edges.forEach((edge) => {
          const source = nodes.find((n) => n.id === edge.source);
          const target = nodes.find((n) => n.id === edge.target);
          if (!source || !target) return;

          const dx = target.x! - source.x!;
          const dy = target.y! - source.y!;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;

          // Spring force towards target distance
          const force = (dist - linkDistance) * linkStrength * alpha;

          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          source.vx = source.vx! + fx;
          source.vy = source.vy! + fy;
          target.vx = target.vx! - fx;
          target.vy = target.vy! - fy;
        });

        // Center gravity (weak pull toward center)
        const centerX = width / 2;
        const centerY = height / 2;
        const centerStrength = 0.05;
        nodes.forEach((node) => {
          const dx = centerX - node.x!;
          const dy = centerY - node.y!;
          node.vx = node.vx! + dx * centerStrength * alpha;
          node.vy = node.vy! + dy * centerStrength * alpha;
        });

        // Cool down
        alpha -= alphaDecay;
      }

      // Update positions with velocity damping
      const velocityDecay = 0.6;
      nodes.forEach((node) => {
        node.vx = node.vx! * velocityDecay;
        node.vy = node.vy! * velocityDecay;
        node.x = node.x! + node.vx!;
        node.y = node.y! + node.vy!;

        // Soft boundary with bounce-back instead of hard clamp
        const margin = 50;
        if (node.x! < margin) {
          node.x = margin;
          node.vx = node.vx! * -0.5;
        } else if (node.x! > width - margin) {
          node.x = width - margin;
          node.vx = node.vx! * -0.5;
        }
        if (node.y! < margin) {
          node.y = margin;
          node.vy = node.vy! * -0.5;
        } else if (node.y! > height - margin) {
          node.y = height - margin;
          node.vy = node.vy! * -0.5;
        }
      });

      // Draw edges
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 1;
      edges.forEach((edge) => {
        const source = nodes.find((n) => n.id === edge.source);
        const target = nodes.find((n) => n.id === edge.target);
        if (!source || !target) return;

        ctx.beginPath();
        ctx.moveTo(source.x!, source.y!);
        ctx.lineTo(target.x!, target.y!);
        ctx.stroke();
      });

      // Draw nodes
      nodes.forEach((node) => {
        const isSelected = selectedNode?.id === node.id;
        const isHovered = hoveredNode === node.id;
        const radius = isSelected || isHovered ? 10 : 8; // Increased from 8/6 for easier clicking

        // Node circle
        ctx.beginPath();
        ctx.arc(node.x!, node.y!, radius, 0, 2 * Math.PI);
        ctx.fillStyle = "#3b82f6"; // Blue for all nodes
        ctx.fill();
        ctx.strokeStyle = isSelected ? "#1e40af" : "#e5e7eb";
        ctx.lineWidth = isSelected ? 3 : 1;
        ctx.stroke();

        // Node label
        if (isSelected || isHovered) {
          ctx.fillStyle = "#1f2937";
          ctx.font = "12px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(node.title, node.x!, node.y! - 12);
        }
      });

      animationRef.current = requestAnimationFrame(animate);
    }

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [graphData, selectedNode, hoveredNode]);

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!graphData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Find clicked node
    const clickedNode = graphData.nodes.find((node) => {
      const dx = x - node.x!;
      const dy = y - node.y!;
      return Math.sqrt(dx * dx + dy * dy) < 12; // Increased from 10 to match larger nodes
    });

    setSelectedNode(clickedNode || null);
  };

  const handleCanvasMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!graphData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Find hovered node
    const hoveredNode = graphData.nodes.find((node) => {
      const dx = x - node.x!;
      const dy = y - node.y!;
      return Math.sqrt(dx * dx + dy * dy) < 12; // Increased from 10 to match larger nodes
    });

    setHoveredNode(hoveredNode?.id || null);
    canvas.style.cursor = hoveredNode ? "pointer" : "default";
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSkeleton}>
            <div className={styles.skeletonTitle}></div>
            <div className={styles.skeletonGraph}></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.errorContainer}>
          <div className={styles.errorCard}>
            <h2 className={styles.errorTitle}>Error</h2>
            <p className={styles.errorMessage}>{error}</p>
            <Link href="/knowledge-base/notes" className={styles.backLink}>
              ← Back to notes
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyContainer}>
          <div className={styles.emptyCard}>
            <Link href="/knowledge-base/notes" className={styles.backLink}>
              ← Back to notes
            </Link>
            <p className={styles.emptyMessage}>
              No notes to visualize yet. Create some notes to see the graph!
            </p>
            <Link href="/knowledge-base/notes/new" className={styles.createButton}>
              Create your first note
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.headerTop}>
            <div className={styles.breadcrumbs}>
              <Link href="/knowledge-base" className={styles.breadcrumbLink}>
                ← Knowledge Base
              </Link>
              <Link href="/knowledge-base/notes" className={styles.breadcrumbLink}>
                All notes
              </Link>
            </div>
            <SettingsDropdown />
          </div>

          <h1 className={styles.title}>Notes Graph</h1>
          <p className={styles.stats}>
            {graphData.count.nodes} notes · {graphData.count.edges} connections
          </p>
        </div>
      </div>

      <div className={styles.main}>
        {/* Graph visualization */}
        <div className={styles.graphCard}>
          <canvas
            ref={canvasRef}
            width={1200}
            height={700}
            onClick={handleCanvasClick}
            onMouseMove={handleCanvasMouseMove}
            className={styles.canvas}
          />

          <div className={styles.legend}>
            <div className={styles.legendItem}>
              <div className={styles.legendDot}></div>
              <span>Notes</span>
            </div>
            <div className={styles.instructions}>Click a node to select · Hover to see title</div>
          </div>
        </div>

        {/* Selected node details */}
        {selectedNode && (
          <div className={styles.selectedNodePanel}>
            <h3 className={styles.nodeTitle}>{selectedNode.title}</h3>
            <div className={styles.nodeMeta}>
              <code className={styles.nodeId}>{selectedNode.id}</code>
              <span>by {selectedNode.author}</span>
            </div>
            {selectedNode.tags.length > 0 && (
              <div className={styles.nodeTags}>
                {selectedNode.tags.map((tag) => (
                  <span key={tag} className={styles.tag}>
                    {tag}
                  </span>
                ))}
              </div>
            )}
            <div className={styles.actions}>
              <Link href={`/knowledge-base/notes/${selectedNode.id}`} className={styles.viewButton}>
                View note
              </Link>
              <button onClick={() => setSelectedNode(null)} className={styles.deselectButton}>
                Deselect
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
