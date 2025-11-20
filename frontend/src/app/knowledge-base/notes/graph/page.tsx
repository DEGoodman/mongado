"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
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
  degree?: number; // Number of connections
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
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [showAllTags, setShowAllTags] = useState(false);
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

        // Calculate node degrees (connection counts)
        const degreeMap = new Map<string, number>();
        data.nodes.forEach((node) => degreeMap.set(node.id, 0));
        data.edges.forEach((edge) => {
          degreeMap.set(edge.source, (degreeMap.get(edge.source) || 0) + 1);
          degreeMap.set(edge.target, (degreeMap.get(edge.target) || 0) + 1);
        });

        // Initialize node positions across the canvas
        const centerX = 450; // Half of canvas width (900)
        const centerY = 311; // Half of canvas height (622)
        const spread = 420; // Initial spread (smaller to keep centered)

        data.nodes = data.nodes.map((node) => ({
          ...node,
          x: centerX + (Math.random() - 0.5) * spread,
          y: centerY + (Math.random() - 0.5) * spread,
          vx: 0,
          vy: 0,
          degree: degreeMap.get(node.id) || 0,
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

  // Get color palette for tags
  const tagColorMap: Record<string, string> = {
    ml: "#8b5cf6", // Purple for ML
    testing: "#3b82f6", // Blue for testing
    experimentation: "#10b981", // Green for experimentation
    sre: "#f59e0b", // Orange for SRE
    management: "#ef4444", // Red for management
    saas: "#ec4899", // Pink for SaaS
    writing: "#06b6d4", // Cyan for writing
    productivity: "#84cc16", // Lime for productivity
    "incident-management": "#dc2626", // Darker red
    culture: "#7c3aed", // Violet
    rollouts: "#0ea5e9", // Sky blue
    "technical-debt": "#f97316", // Deep orange
  };

  // Generate color for any tag
  const getTagColor = (tag: string): string => {
    if (tagColorMap[tag.toLowerCase()]) {
      return tagColorMap[tag.toLowerCase()];
    }
    // Generate consistent color based on tag name
    let hash = 0;
    for (let i = 0; i < tag.length; i++) {
      hash = tag.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = hash % 360;
    return `hsl(${hue}, 65%, 55%)`;
  };

  // Color palette for different tags
  const getNodeColor = (node: GraphNode): string => {
    if (!node.tags || node.tags.length === 0) {
      return "#94a3b8"; // Gray for untagged
    }

    return getTagColor(node.tags[0]); // Use first tag
  };

  // Get most common tags from the graph
  const getTopTags = (limit: number = 12): Array<{ tag: string; count: number; color: string }> => {
    if (!graphData) return [];

    const tagCounts = new Map<string, number>();
    graphData.nodes.forEach((node) => {
      node.tags.forEach((tag) => {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
      });
    });

    return Array.from(tagCounts.entries())
      .map(([tag, count]) => ({ tag, count, color: getTagColor(tag) }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit);
  };

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
    const alphaDecay = 0.01; // Moderate cooling speed
    const alphaMin = 0.001; // Stop when alpha gets this low
    let frameCount = 0;

    function animate() {
      if (!ctx) return;
      frameCount++;

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Only apply forces if simulation is still cooling
      if (alpha > alphaMin) {
        // Repulsion between all nodes (charge force)
        const chargeStrength = 3000; // Very strong to spread nodes across canvas
        const minDistance = 30; // Prevent nodes from getting too close

        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const dx = nodes[j].x! - nodes[i].x!;
            const dy = nodes[j].y! - nodes[i].y!;
            const distSq = Math.max(dx * dx + dy * dy, minDistance * minDistance);
            const dist = Math.sqrt(distSq);

            // Repulsion force (inverse square law)
            const force = Math.min((chargeStrength / distSq) * alpha, 15); // Higher cap for stronger push

            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            nodes[i].vx = nodes[i].vx! - fx;
            nodes[i].vy = nodes[i].vy! - fy;
            nodes[j].vx = nodes[j].vx! + fx;
            nodes[j].vy = nodes[j].vy! + fy;
          }
        }

        // Attraction along edges (spring force)
        const linkStrength = 0.1;
        const linkDistance = 180; // Even longer links to spread out connected nodes
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

        // Center gravity (very weak pull toward center)
        const centerX = width / 2;
        const centerY = height / 2;
        const centerStrength = 0.003; // Minimal gravity to allow maximum spreading
        nodes.forEach((node) => {
          const dx = centerX - node.x!;
          const dy = centerY - node.y!;
          node.vx = node.vx! + dx * centerStrength * alpha;
          node.vy = node.vy! + dy * centerStrength * alpha;
        });

        // Cool down (ensure alpha doesn't go negative)
        alpha = Math.max(alphaMin, alpha - alphaDecay);
      }

      // Update positions with velocity damping
      const velocityDecay = 0.55; // Even less damping to allow nodes to spread

      nodes.forEach((node) => {
        // Cap maximum velocity to prevent nodes from shooting off
        const maxVelocity = 15; // Higher velocity to allow faster spreading
        node.vx = Math.max(-maxVelocity, Math.min(maxVelocity, node.vx! * velocityDecay));
        node.vy = Math.max(-maxVelocity, Math.min(maxVelocity, node.vy! * velocityDecay));

        node.x = node.x! + node.vx!;
        node.y = node.y! + node.vy!;

        // Keep nodes strictly within bounds (larger margin for text labels)
        const margin = 70;

        if (node.x! < margin) {
          node.x = margin;
          node.vx = Math.abs(node.vx!) * 0.5; // Bounce back
        } else if (node.x! > width - margin) {
          node.x = width - margin;
          node.vx = -Math.abs(node.vx!) * 0.5; // Bounce back
        }
        if (node.y! < margin) {
          node.y = margin;
          node.vy = Math.abs(node.vy!) * 0.5; // Bounce back
        } else if (node.y! > height - margin) {
          node.y = height - margin;
          node.vy = -Math.abs(node.vy!) * 0.5; // Bounce back
        }
      });

      // Check if tag filtering is active
      const isFiltering = selectedTags.size > 0;

      // Draw edges (draw before nodes so nodes appear on top)
      edges.forEach((edge) => {
        const source = nodes.find((n) => n.id === edge.source);
        const target = nodes.find((n) => n.id === edge.target);
        if (!source || !target) return;

        // Check if edge should be dimmed based on tag filter
        const sourceMatches = !isFiltering || source.tags.some((tag) => selectedTags.has(tag));
        const targetMatches = !isFiltering || target.tags.some((tag) => selectedTags.has(tag));
        const isDimmed = isFiltering && !sourceMatches && !targetMatches;

        // Check if edge connects large/hub nodes (high degree nodes)
        const isHubEdge = (source.degree || 0) >= 6 || (target.degree || 0) >= 6;

        // Highlight edges connected to hovered/selected nodes
        const isHighlighted =
          (selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id)) ||
          (hoveredNode && (edge.source === hoveredNode || edge.target === hoveredNode));

        ctx.beginPath();
        ctx.moveTo(source.x!, source.y!);
        ctx.lineTo(target.x!, target.y!);

        if (isHighlighted) {
          ctx.strokeStyle = "#3b82f6";
          ctx.lineWidth = 3;
          ctx.globalAlpha = 1;
        } else if (isDimmed) {
          ctx.strokeStyle = "#e2e8f0";
          ctx.lineWidth = 0.5;
          ctx.globalAlpha = 0.2;
        } else if (isHubEdge) {
          ctx.strokeStyle = "#64748b";
          ctx.lineWidth = 2;
          ctx.globalAlpha = 1;
        } else {
          ctx.strokeStyle = "#cbd5e1";
          ctx.lineWidth = 1;
          ctx.globalAlpha = 1;
        }
        ctx.stroke();
        ctx.globalAlpha = 1; // Reset
      });

      // Draw nodes
      nodes.forEach((node) => {
        const isSelected = selectedNode?.id === node.id;
        const isHovered = hoveredNode === node.id;

        // Check if node matches tag filter
        const matchesFilter = !isFiltering || node.tags.some((tag) => selectedTags.has(tag));
        const isDimmed = isFiltering && !matchesFilter;

        // Scale radius based on degree (connection count)
        const degree = node.degree || 0;
        let baseRadius: number;
        if (degree >= 10) {
          baseRadius = 28; // Hub nodes (10+ connections)
        } else if (degree >= 6) {
          baseRadius = 22; // Large nodes (6-9 connections)
        } else if (degree >= 3) {
          baseRadius = 16; // Medium nodes (3-5 connections)
        } else if (degree >= 1) {
          baseRadius = 10; // Small nodes (1-2 connections)
        } else {
          baseRadius = 8; // Orphan nodes (0 connections)
        }
        const radius = isSelected || isHovered ? baseRadius * 1.15 : baseRadius;

        // Get color based on tags
        const nodeColor = getNodeColor(node);

        // Set opacity for dimmed nodes
        ctx.globalAlpha = isDimmed ? 0.15 : 1;

        // Node circle
        ctx.beginPath();
        ctx.arc(node.x!, node.y!, radius, 0, 2 * Math.PI);
        ctx.fillStyle = nodeColor;
        ctx.fill();

        // Border
        if (isSelected) {
          ctx.strokeStyle = "#1e40af";
          ctx.lineWidth = 4;
        } else if (degree >= 6) {
          ctx.strokeStyle = "#334155"; // Darker border for large/hub nodes
          ctx.lineWidth = 2;
        } else {
          ctx.strokeStyle = "#374151";
          ctx.lineWidth = 1;
        }
        ctx.stroke();

        // Node label - only show on hover or selected
        if (isSelected || isHovered) {
          ctx.fillStyle = "#1f2937";
          ctx.font = degree >= 6 ? "bold 13px sans-serif" : "12px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(node.title, node.x!, node.y! - baseRadius - 6);

          // Show degree count only when hovered/selected
          if (node.degree && node.degree > 0) {
            ctx.font = "10px sans-serif";
            ctx.fillStyle = "#64748b";
            ctx.fillText(`${node.degree} links`, node.x!, node.y! + baseRadius + 14);
          }
        }

        ctx.globalAlpha = 1; // Reset
      });

      animationRef.current = requestAnimationFrame(animate);
    }

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [graphData, selectedNode, hoveredNode, selectedTags]);

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!graphData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();

    // Scale from CSS pixels to canvas pixels
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;

    // Find clicked node (use radius based on degree + padding for easier clicking)
    const clickedNode = graphData.nodes.find((node) => {
      const dx = x - node.x!;
      const dy = y - node.y!;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const degree = node.degree || 0;
      let clickRadius: number;
      if (degree >= 10) clickRadius = 32;
      else if (degree >= 6) clickRadius = 26;
      else if (degree >= 3) clickRadius = 20;
      else if (degree >= 1) clickRadius = 14;
      else clickRadius = 12; // Orphan nodes
      return dist < clickRadius;
    });

    setSelectedNode(clickedNode || null);
  };

  const handleCanvasMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!graphData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();

    // Scale from CSS pixels to canvas pixels
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;

    // Find hovered node (use radius based on degree + padding)
    const hoveredNode = graphData.nodes.find((node) => {
      const dx = x - node.x!;
      const dy = y - node.y!;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const degree = node.degree || 0;
      let hoverRadius: number;
      if (degree >= 10) hoverRadius = 32;
      else if (degree >= 6) hoverRadius = 26;
      else if (degree >= 3) hoverRadius = 20;
      else if (degree >= 1) hoverRadius = 14;
      else hoverRadius = 12;
      return dist < hoverRadius;
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
          </div>

          <div className={styles.titleRow}>
            <h1 className={styles.title}>Notes Graph</h1>
            <span className={styles.stats}>
              {graphData.count.nodes} notes · {graphData.count.edges} connections
            </span>
          </div>
        </div>
      </div>

      <div className={styles.main}>
        <div className={styles.gridLayout}>
          {/* Graph visualization - Left column */}
          <div className={styles.graphCard}>
            <canvas
              ref={canvasRef}
              width={900}
              height={622}
              onClick={handleCanvasClick}
              onMouseMove={handleCanvasMouseMove}
              className={styles.canvas}
            />
            <div className={styles.instructions}>
              Hover over nodes to see titles and connections · Larger nodes = hub notes with more
              links
            </div>
          </div>

          {/* Sidebar - Right column */}
          <div className={styles.sidebar}>
            {/* Selected node details */}
            {selectedNode && (
              <div className={styles.selectedNodePanel}>
                <h3 className={styles.nodeTitle}>{selectedNode.title}</h3>
                <div className={styles.nodeMeta}>
                  <code className={styles.nodeId}>{selectedNode.id}</code>
                  <span>by {selectedNode.author}</span>
                  <span className={styles.nodeConnections}>
                    {selectedNode.degree || 0} connection{selectedNode.degree !== 1 ? "s" : ""}
                  </span>
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
                  <Link
                    href={`/knowledge-base/notes/${selectedNode.id}`}
                    className={styles.viewButton}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View note
                  </Link>
                  <button onClick={() => setSelectedNode(null)} className={styles.deselectButton}>
                    Deselect
                  </button>
                </div>
              </div>
            )}

            {/* Tag filters */}
            <div className={styles.filterSection}>
              <h4 className={styles.filterTitle}>Filter by tag</h4>
              <div className={`${styles.tagList} ${showAllTags ? styles.tagListScrollable : ""}`}>
                {getTopTags(showAllTags ? 50 : 10).map(({ tag, count, color }) => {
                  const isActive = selectedTags.has(tag);
                  return (
                    <button
                      key={tag}
                      onClick={() => {
                        const newTags = new Set(selectedTags);
                        if (isActive) {
                          newTags.delete(tag);
                        } else {
                          newTags.add(tag);
                        }
                        setSelectedTags(newTags);
                      }}
                      className={`${styles.tagButton} ${isActive ? styles.tagButtonActive : ""}`}
                      style={{
                        borderColor: isActive ? color : undefined,
                        backgroundColor: isActive ? `${color}15` : undefined,
                        color: isActive ? color : undefined,
                      }}
                    >
                      <span className={styles.tagDot} style={{ backgroundColor: color }} />
                      <span className={styles.tagName}>{tag}</span>
                      <span className={styles.tagCount}>({count})</span>
                    </button>
                  );
                })}
              </div>
              <div className={styles.filterActions}>
                {getTopTags(50).length > 10 && (
                  <button
                    onClick={() => setShowAllTags(!showAllTags)}
                    className={styles.showAllButton}
                  >
                    {showAllTags ? "Show less" : `Show all (${getTopTags(50).length})`}
                  </button>
                )}
                {selectedTags.size > 0 && (
                  <button onClick={() => setSelectedTags(new Set())} className={styles.clearButton}>
                    Clear filters
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
