"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import * as d3 from "d3";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  title: string;
  author: string;
  tags: string[];
  degree?: number;
  radius?: number;
}

interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  count: {
    nodes: number;
    edges: number;
  };
}

function NotesGraphContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nodeParam = searchParams.get("node");

  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [filterLogic, setFilterLogic] = useState<"OR" | "AND">("OR");
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null);
  const selectedNodeIdRef = useRef<string | null>(null);

  // Keep ref in sync with state
  useEffect(() => {
    selectedNodeIdRef.current = selectedNode?.id || null;
  }, [selectedNode]);

  useEffect(() => {
    async function fetchGraphData() {
      try {
        setLoading(true);
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

        const token = localStorage.getItem("admin_token");
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

        // Calculate node degrees
        const degreeMap = new Map<string, number>();
        data.nodes.forEach((node) => degreeMap.set(node.id, 0));
        data.edges.forEach((edge) => {
          const sourceId = typeof edge.source === "string" ? edge.source : edge.source.id;
          const targetId = typeof edge.target === "string" ? edge.target : edge.target.id;
          degreeMap.set(sourceId, (degreeMap.get(sourceId) || 0) + 1);
          degreeMap.set(targetId, (degreeMap.get(targetId) || 0) + 1);
        });

        // Set degree and radius for each node
        data.nodes = data.nodes.map((node) => {
          const degree = degreeMap.get(node.id) || 0;
          let radius: number;
          if (degree >= 10) radius = 28;
          else if (degree >= 6) radius = 22;
          else if (degree >= 3) radius = 16;
          else if (degree >= 1) radius = 10;
          else radius = 8;

          return {
            ...node,
            degree,
            radius,
          };
        });

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

  // Handle URL parameter for pre-selected node
  useEffect(() => {
    if (nodeParam && graphData) {
      const node = graphData.nodes.find((n) => n.id === nodeParam);
      if (node) {
        setSelectedNode(node);
        logger.info("Node pre-selected from URL param", { nodeId: nodeParam });
      } else {
        logger.warn("Node from URL param not found in graph", { nodeId: nodeParam });
      }
    }
  }, [nodeParam, graphData]);

  // Tag color utilities
  const tagColorMap: Record<string, string> = {
    ml: "#8b5cf6",
    testing: "#3b82f6",
    experimentation: "#10b981",
    sre: "#f59e0b",
    management: "#ef4444",
    saas: "#ec4899",
    writing: "#06b6d4",
    productivity: "#84cc16",
    "incident-management": "#dc2626",
    culture: "#7c3aed",
    rollouts: "#0ea5e9",
    "technical-debt": "#f97316",
  };

  const getTagColor = (tag: string): string => {
    if (tagColorMap[tag.toLowerCase()]) {
      return tagColorMap[tag.toLowerCase()];
    }
    let hash = 0;
    for (let i = 0; i < tag.length; i++) {
      hash = tag.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = hash % 360;
    return `hsl(${hue}, 65%, 55%)`;
  };

  const getNodeColor = (node: GraphNode): string => {
    if (!node.tags || node.tags.length === 0) {
      return "#94a3b8";
    }
    return getTagColor(node.tags[0]);
  };

  const getAllTags = (): Array<{ tag: string; count: number; color: string }> => {
    if (!graphData) return [];

    const tagCounts = new Map<string, number>();
    graphData.nodes.forEach((node) => {
      node.tags.forEach((tag) => {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
      });
    });

    return Array.from(tagCounts.entries())
      .map(([tag, count]) => ({ tag, count, color: getTagColor(tag) }))
      .sort((a, b) => b.count - a.count);
  };

  // D3 Force Simulation
  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = 900;
    const height = 622;

    // Clear previous content
    svg.selectAll("*").remove();

    // Add glow filter
    const defs = svg.append("defs");
    const glowFilter = defs
      .append("filter")
      .attr("id", "glow")
      .attr("x", "-50%")
      .attr("y", "-50%")
      .attr("width", "200%")
      .attr("height", "200%");

    glowFilter.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "coloredBlur");

    const feMerge = glowFilter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // Add drop shadow filter for labels
    const textShadow = defs
      .append("filter")
      .attr("id", "textShadow")
      .attr("x", "-50%")
      .attr("y", "-50%")
      .attr("width", "200%")
      .attr("height", "200%");

    textShadow
      .append("feDropShadow")
      .attr("dx", 0)
      .attr("dy", 1)
      .attr("stdDeviation", 2)
      .attr("flood-color", "#000")
      .attr("flood-opacity", 0.3);

    const nodes = graphData.nodes;
    const edges = graphData.edges;

    // Create simulation
    const simulation = d3
      .forceSimulation<GraphNode>(nodes)
      .force(
        "charge",
        d3.forceManyBody<GraphNode>().strength(-300).distanceMin(20).distanceMax(400)
      )
      .force("center", d3.forceCenter(width / 2, height / 2).strength(0.05))
      .force(
        "link",
        d3
          .forceLink<GraphNode, GraphEdge>(edges)
          .id((d) => d.id)
          .distance((link) => {
            const source = link.source as GraphNode;
            const target = link.target as GraphNode;
            const avgConnections = ((source.degree || 1) + (target.degree || 1)) / 2;
            return 40 + avgConnections * 3;
          })
          .strength(0.4)
      )
      .force(
        "collision",
        d3
          .forceCollide<GraphNode>()
          .radius((d) => (d.radius || 10) + 5)
          .strength(0.5)
          .iterations(1)
      )
      .alphaDecay(0.03)
      .velocityDecay(0.4);

    simulationRef.current = simulation;

    // Create container groups for proper z-ordering
    const linkGroup = svg.append("g").attr("class", "links");
    const nodeGroup = svg.append("g").attr("class", "nodes");
    const labelGroup = svg.append("g").attr("class", "labels");

    // Create links
    const linkElements = linkGroup
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", "#9ca3af")
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.4);

    // Create nodes
    const nodeElements = nodeGroup
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => d.radius || 10)
      .attr("fill", (d) => getNodeColor(d))
      .attr("stroke", "#374151")
      .attr("stroke-width", 1)
      .attr("cursor", "pointer");

    // Create labels (hidden by default)
    const labelElements = labelGroup
      .selectAll("text")
      .data(nodes)
      .join("text")
      .attr("text-anchor", "start")
      .attr("filter", "url(#textShadow)")
      .style("font-size", "13px")
      .style("font-weight", "500")
      .style("fill", "#1f2937")
      .style("paint-order", "stroke")
      .style("stroke", "#ffffff")
      .style("stroke-width", "4px")
      .style("stroke-linejoin", "round")
      .style("opacity", 0)
      .style("pointer-events", "none")
      .text((d) => d.title || d.id);

    // Helper function to get connected node IDs
    function getConnectedNodeIds(node: GraphNode): string[] {
      return edges
        .filter((link) => {
          const sourceId = typeof link.source === "string" ? link.source : link.source.id;
          const targetId = typeof link.target === "string" ? link.target : link.target.id;
          return sourceId === node.id || targetId === node.id;
        })
        .map((link) => {
          const sourceId = typeof link.source === "string" ? link.source : link.source.id;
          const targetId = typeof link.target === "string" ? link.target : link.target.id;
          return sourceId === node.id ? targetId : sourceId;
        });
    }

    // Reset to selected state
    function resetToSelectedState() {
      const currentSelectedId = selectedNodeIdRef.current;
      if (!currentSelectedId) return;

      const selectedNodeData = nodes.find((n) => n.id === currentSelectedId);
      if (!selectedNodeData) return;

      const connectedIds = getConnectedNodeIds(selectedNodeData);

      nodeElements
        .transition()
        .duration(150)
        .attr("opacity", (d) => {
          if (d.id === currentSelectedId) return 1.0;
          if (connectedIds.includes(d.id)) return 1.0;
          return 0.35;
        })
        .attr("r", (d) => {
          if (d.id === currentSelectedId) return (d.radius || 10) * 1.4;
          return d.radius || 10;
        })
        .attr("stroke", (d) => (d.id === currentSelectedId ? "#9333ea" : "#374151"))
        .attr("stroke-width", (d) => (d.id === currentSelectedId ? 4 : 1))
        .attr("filter", null);

      linkElements
        .transition()
        .duration(150)
        .attr("stroke-opacity", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === currentSelectedId || targetId === currentSelectedId;
          return isConnected ? 0.7 : 0.08;
        })
        .attr("stroke-width", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === currentSelectedId || targetId === currentSelectedId;
          return isConnected ? 2.5 : 1;
        })
        .attr("stroke", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === currentSelectedId || targetId === currentSelectedId;
          return isConnected ? "#9333ea" : "#9ca3af";
        });

      labelElements
        .transition()
        .duration(150)
        .style("opacity", (d) => {
          if (d.id === currentSelectedId) return 1.0;
          if (connectedIds.includes(d.id)) return 0.75;
          return 0;
        })
        .style("font-weight", (d) => (d.id === currentSelectedId ? "700" : "500"))
        .style("font-size", (d) => (d.id === currentSelectedId ? "15px" : "13px"));
    }

    // Reset to default state
    function resetToDefault() {
      nodeElements
        .transition()
        .duration(150)
        .attr("opacity", 1.0)
        .attr("r", (d) => d.radius || 10)
        .attr("stroke", "#374151")
        .attr("stroke-width", 1)
        .attr("filter", null);

      linkElements
        .transition()
        .duration(150)
        .attr("stroke-opacity", 0.4)
        .attr("stroke-width", 1)
        .attr("stroke", "#9ca3af");

      labelElements.transition().duration(150).style("opacity", 0);
    }

    // Hover handlers
    function handleNodeHover(_event: MouseEvent, hoveredNode: GraphNode) {
      const connectedIds = getConnectedNodeIds(hoveredNode);

      // Bring hovered cluster to front
      nodeElements.each(function (d) {
        if (d.id === hoveredNode.id || connectedIds.includes(d.id)) {
          (this as SVGElement).parentNode?.appendChild(this as SVGElement);
        }
      });

      linkElements.each(function (d) {
        const sourceId = typeof d.source === "string" ? d.source : d.source.id;
        const targetId = typeof d.target === "string" ? d.target : d.target.id;
        if (sourceId === hoveredNode.id || targetId === hoveredNode.id) {
          (this as SVGElement).parentNode?.appendChild(this as SVGElement);
        }
      });

      // Visual highlighting - nodes
      nodeElements
        .transition()
        .duration(150)
        .attr("opacity", (d) => {
          if (d.id === hoveredNode.id) return 1.0;
          if (connectedIds.includes(d.id)) return 1.0;
          return 0.25;
        })
        .attr("r", (d) => {
          if (d.id === hoveredNode.id) return (d.radius || 10) * 1.3;
          return d.radius || 10;
        })
        .attr("filter", (d) => (d.id === hoveredNode.id ? "url(#glow)" : null))
        .attr("stroke", (d) => (d.id === hoveredNode.id ? "#ffffff" : "#374151"))
        .attr("stroke-width", (d) => (d.id === hoveredNode.id ? 4 : 1));

      // Visual highlighting - links
      linkElements
        .transition()
        .duration(150)
        .attr("stroke-opacity", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === hoveredNode.id || targetId === hoveredNode.id;
          return isConnected ? 0.8 : 0.05;
        })
        .attr("stroke-width", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === hoveredNode.id || targetId === hoveredNode.id;
          return isConnected ? 2.5 : 1;
        })
        .attr("stroke", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === hoveredNode.id || targetId === hoveredNode.id;
          return isConnected ? "#2563eb" : "#9ca3af";
        });

      // Show labels for hovered cluster
      labelElements
        .transition()
        .duration(150)
        .style("opacity", (d) => {
          if (d.id === hoveredNode.id) return 1.0;
          if (connectedIds.includes(d.id)) return 0.85;
          return 0;
        })
        .style("font-weight", (d) => (d.id === hoveredNode.id ? "600" : "500"))
        .style("font-size", (d) => (d.id === hoveredNode.id ? "14px" : "13px"));
    }

    function handleNodeLeave() {
      if (selectedNodeIdRef.current) {
        resetToSelectedState();
      } else {
        resetToDefault();
      }
    }

    function handleNodeClick(_event: MouseEvent, clickedNode: GraphNode) {
      setSelectedNode(clickedNode);
    }

    // Attach event handlers
    nodeElements
      .on("mouseenter", handleNodeHover)
      .on("mouseleave", handleNodeLeave)
      .on("click", handleNodeClick);

    // Enable dragging
    const drag = d3
      .drag<SVGCircleElement, GraphNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    nodeElements.call(
      drag as unknown as (
        selection: d3.Selection<d3.BaseType | SVGCircleElement, GraphNode, SVGGElement, unknown>
      ) => void
    );

    // Update positions on tick
    simulation.on("tick", () => {
      // Soft boundary constraint - gentle push away from edges
      const padding = 45;
      const softness = 0.08;
      nodes.forEach((node) => {
        if ((node.x || 0) < padding) {
          node.vx = (node.vx || 0) + (padding - (node.x || 0)) * softness;
        }
        if ((node.x || 0) > width - padding) {
          node.vx = (node.vx || 0) + (width - padding - (node.x || 0)) * softness;
        }
        if ((node.y || 0) < padding) {
          node.vy = (node.vy || 0) + (padding - (node.y || 0)) * softness;
        }
        if ((node.y || 0) > height - padding) {
          node.vy = (node.vy || 0) + (height - padding - (node.y || 0)) * softness;
        }
      });

      linkElements
        .attr("x1", (d) => (d.source as GraphNode).x || 0)
        .attr("y1", (d) => (d.source as GraphNode).y || 0)
        .attr("x2", (d) => (d.target as GraphNode).x || 0)
        .attr("y2", (d) => (d.target as GraphNode).y || 0);

      nodeElements.attr("cx", (d) => d.x || 0).attr("cy", (d) => d.y || 0);

      // Labels positioned to right of nodes, or left if near edge
      const labelThreshold = width - 150;
      labelElements
        .attr("x", (d) => {
          const nodeX = d.x || 0;
          const nodeRadius = d.radius || 10;
          if (nodeX > labelThreshold) {
            // Position to left of node
            return nodeX - nodeRadius - 8;
          }
          // Position to right of node
          return nodeX + nodeRadius + 8;
        })
        .attr("y", (d) => (d.y || 0) + 4)
        .attr("text-anchor", (d) => ((d.x || 0) > labelThreshold ? "end" : "start"));
    });

    // Click on SVG background to deselect
    svg.on("click", (event) => {
      if (event.target === svg.node()) {
        setSelectedNode(null);
      }
    });

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [graphData]);

  // Separate effect for visual updates (selection, filters) without recreating simulation
  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const nodeElements = svg.selectAll<SVGCircleElement, GraphNode>("circle");
    const linkElements = svg.selectAll<SVGLineElement, GraphEdge>("line");
    const labelElements = svg.selectAll<SVGTextElement, GraphNode>("text");

    if (nodeElements.empty()) return;

    const edges = graphData.edges;
    const selectedNodeId = selectedNode?.id || null;
    const selectedTagsArray = Array.from(selectedTags);
    const isFiltering = selectedTags.size > 0;

    // Helper function
    function getConnectedNodeIds(nodeId: string): string[] {
      return edges
        .filter((link) => {
          const sourceId = typeof link.source === "string" ? link.source : link.source.id;
          const targetId = typeof link.target === "string" ? link.target : link.target.id;
          return sourceId === nodeId || targetId === nodeId;
        })
        .map((link) => {
          const sourceId = typeof link.source === "string" ? link.source : link.source.id;
          const targetId = typeof link.target === "string" ? link.target : link.target.id;
          return sourceId === nodeId ? targetId : sourceId;
        });
    }

    // Apply selection state
    if (selectedNodeId) {
      const connectedIds = getConnectedNodeIds(selectedNodeId);

      nodeElements
        .transition()
        .duration(150)
        .attr("opacity", (d) => {
          if (d.id === selectedNodeId) return 1.0;
          if (connectedIds.includes(d.id)) return 1.0;
          return 0.35;
        })
        .attr("r", (d) => {
          if (d.id === selectedNodeId) return (d.radius || 10) * 1.4;
          return d.radius || 10;
        })
        .attr("stroke", (d) => (d.id === selectedNodeId ? "#9333ea" : "#374151"))
        .attr("stroke-width", (d) => (d.id === selectedNodeId ? 4 : 1))
        .attr("filter", null);

      linkElements
        .transition()
        .duration(150)
        .attr("stroke-opacity", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === selectedNodeId || targetId === selectedNodeId;
          return isConnected ? 0.7 : 0.08;
        })
        .attr("stroke-width", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === selectedNodeId || targetId === selectedNodeId;
          return isConnected ? 2.5 : 1;
        })
        .attr("stroke", (d) => {
          const sourceId = typeof d.source === "string" ? d.source : d.source.id;
          const targetId = typeof d.target === "string" ? d.target : d.target.id;
          const isConnected = sourceId === selectedNodeId || targetId === selectedNodeId;
          return isConnected ? "#9333ea" : "#9ca3af";
        });

      labelElements
        .transition()
        .duration(150)
        .style("opacity", (d) => {
          if (d.id === selectedNodeId) return 1.0;
          if (connectedIds.includes(d.id)) return 0.75;
          return 0;
        })
        .style("font-weight", (d) => (d.id === selectedNodeId ? "700" : "500"))
        .style("font-size", (d) => (d.id === selectedNodeId ? "15px" : "13px"));
    } else if (isFiltering) {
      // Apply tag filtering
      nodeElements
        .transition()
        .duration(200)
        .attr("opacity", (d) => {
          const matchedTags = selectedTagsArray.filter((tag) => d.tags?.includes(tag));

          if (filterLogic === "AND") {
            return matchedTags.length === selectedTagsArray.length ? 1.0 : 0.15;
          } else {
            if (matchedTags.length === 0) return 0.15;
            const matchRatio = matchedTags.length / selectedTagsArray.length;
            return 0.4 + matchRatio * 0.6;
          }
        })
        .attr("r", (d) => d.radius || 10)
        .attr("stroke", (d) => {
          const matchedTags = selectedTagsArray.filter((tag) => d.tags?.includes(tag));
          if (filterLogic === "AND" && matchedTags.length === selectedTagsArray.length) {
            return "#9333ea";
          }
          return "#374151";
        })
        .attr("stroke-width", (d) => {
          const matchedTags = selectedTagsArray.filter((tag) => d.tags?.includes(tag));
          if (filterLogic === "AND" && matchedTags.length === selectedTagsArray.length) {
            return 3;
          }
          return 1;
        })
        .attr("filter", null);

      linkElements
        .transition()
        .duration(200)
        .attr("stroke-opacity", (d) => {
          const source = d.source as GraphNode;
          const target = d.target as GraphNode;

          const sourceMatchedTags = selectedTagsArray.filter((tag) => source.tags?.includes(tag));
          const targetMatchedTags = selectedTagsArray.filter((tag) => target.tags?.includes(tag));

          let sourceVisible: boolean;
          let targetVisible: boolean;

          if (filterLogic === "AND") {
            sourceVisible = sourceMatchedTags.length === selectedTagsArray.length;
            targetVisible = targetMatchedTags.length === selectedTagsArray.length;
          } else {
            sourceVisible = sourceMatchedTags.length > 0;
            targetVisible = targetMatchedTags.length > 0;
          }

          return sourceVisible && targetVisible ? 0.3 : 0.05;
        });

      labelElements.transition().duration(150).style("opacity", 0);
    } else {
      // Reset to default
      nodeElements
        .transition()
        .duration(150)
        .attr("opacity", 1.0)
        .attr("r", (d) => d.radius || 10)
        .attr("stroke", "#374151")
        .attr("stroke-width", 1)
        .attr("filter", null);

      linkElements
        .transition()
        .duration(150)
        .attr("stroke-opacity", 0.4)
        .attr("stroke-width", 1)
        .attr("stroke", "#9ca3af");

      labelElements.transition().duration(150).style("opacity", 0);
    }
  }, [selectedNode, selectedTags, filterLogic, graphData]);

  // Handle deselect
  const handleDeselect = () => {
    setSelectedNode(null);
    // Remove node query param from URL
    router.push("/knowledge-base/notes/graph");
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
            <svg
              ref={svgRef}
              viewBox="0 0 900 622"
              preserveAspectRatio="xMidYMid meet"
              className={styles.canvas}
              style={{ display: "block", width: "100%", height: "100%" }}
            />
            <div className={styles.instructions}>
              Hover over nodes to see titles and connections · Drag nodes to reposition · Larger
              nodes = hub notes with more links
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
                  <button onClick={handleDeselect} className={styles.deselectButton}>
                    Deselect
                  </button>
                </div>
              </div>
            )}

            {/* Tag filters */}
            <div className={styles.filterSection}>
              <div className={styles.filterControls}>
                <h4 className={styles.filterTitle}>Filter by tag</h4>
                <div className={styles.filterLogic}>
                  <button
                    className={filterLogic === "OR" ? styles.active : ""}
                    onClick={() => setFilterLogic("OR")}
                  >
                    Any
                  </button>
                  <button
                    className={filterLogic === "AND" ? styles.active : ""}
                    onClick={() => setFilterLogic("AND")}
                  >
                    All
                  </button>
                </div>
              </div>
              <div className={styles.tagList}>
                {getAllTags().map(({ tag, count, color }) => {
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
              {selectedTags.size > 0 && (
                <div className={styles.filterActions}>
                  <button onClick={() => setSelectedTags(new Set())} className={styles.clearButton}>
                    Clear filters
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NotesGraphPage() {
  return (
    <Suspense fallback={<div>Loading graph...</div>}>
      <NotesGraphContent />
    </Suspense>
  );
}
