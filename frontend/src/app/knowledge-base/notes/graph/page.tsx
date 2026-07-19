"use client";

import { useEffect, useState, useRef, Suspense, useCallback, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type Simulation,
  type SimulationNodeDatum,
} from "d3-force";
import { drag as d3Drag } from "d3-drag";
import { pointer, select, type BaseType, type Selection } from "d3-selection";
import { logger } from "@/lib/logger";
import { LoadingState, ErrorState, EmptyState } from "@/components/PageState";
import styles from "./page.module.scss";

const graphLog = logger.withContext("Graph");

// Distinguishes parallel or zombie component instances in the logs — the
// signature failure mode for this page is a stale scene from a dead instance
// (Fast Refresh / polluted .next) swallowing events meant for the live one
let instanceCounter = 0;

interface GraphNode extends SimulationNodeDatum {
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

// Tag color map - module-level constant for consistent coloring
// Colors drawn from the design-system scales (orange/terracotta/mustard/
// teal/slate/dusty-blue/sage) so the graph reads as part of the site.
const TAG_COLOR_MAP: Record<string, string> = {
  ml: "#5B6F8F", // slate-blue-600
  testing: "#4278A8", // dusty-blue-600
  experimentation: "#3A8A7D", // teal-600
  sre: "#D4A748", // mustard-500
  management: "#C4624F", // terracotta-600
  saas: "#D18573", // terracotta-500
  writing: "#6BB8AB", // teal-400
  productivity: "#7B9E7A", // sage-500
  "incident-management": "#B91C1C", // red-700
  culture: "#91A4BF", // slate-blue-400
  rollouts: "#5790BF", // dusty-blue-500
  "technical-debt": "#D96D32", // orange-600
  operations: "#7388A8", // slate-blue-500
  architecture: "#4A5A74", // slate-blue-700
  leadership: "#9CB89B", // sage-400
  "system-design": "#A8503E", // terracotta-700
  engineering: "#E8773C", // orange-500
  "data-engineering": "#4A9D8E", // teal-500
  "best-practices": "#B8903D", // mustard-600
  api: "#D99B8D", // terracotta-400
  "ci-cd": "#6B8B6B", // sage-600
  git: "#73A5CD", // dusty-blue-400
};

const EMPTY_SET: ReadonlySet<string> = new Set<string>();

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
  const simulationRef = useRef<Simulation<GraphNode, GraphEdge> | null>(null);
  const selectedNodeIdRef = useRef<string | null>(null);

  const instanceRef = useRef(0);
  if (instanceRef.current === 0) instanceRef.current = ++instanceCounter;
  const iid = instanceRef.current;
  // Dev-only diagnostics (logger.debug is a no-op in production): every
  // line carries the component-instance id to expose zombie instances
  const ilog = useCallback(
    (msg: string, data?: unknown) =>
      data === undefined
        ? graphLog.debug(`i${iid} ${msg}`)
        : graphLog.debug(`i${iid} ${msg}`, data),
    [iid]
  );

  // Keep ref in sync with state
  useEffect(() => {
    selectedNodeIdRef.current = selectedNode?.id || null;
  }, [selectedNode]);

  useEffect(() => {
    ilog("component mounted");
    return () => ilog("component unmounted");
  }, [ilog]);

  // Drop a stale ?node= param so it can't re-select the old node
  const clearNodeParam = useCallback(() => {
    if (window.location.search.includes("node=")) {
      router.replace("/knowledge-base/notes/graph", { scroll: false });
    }
  }, [router]);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    async function fetchGraphData() {
      try {
        setLoading(true);
        ilog("fetching graph data");
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
          signal: controller.signal,
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

        if (cancelled) {
          ilog("fetch resolved after cleanup — ignored");
          return;
        }
        setGraphData(data);
        ilog("graph data loaded", { nodes: data.count.nodes, edges: data.count.edges });
      } catch (err) {
        if (cancelled || (err instanceof DOMException && err.name === "AbortError")) {
          ilog("fetch aborted by cleanup");
          return;
        }
        const message = err instanceof Error ? err.message : "Failed to load graph";
        setError(message);
        logger.error("Failed to load graph data", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchGraphData();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [ilog]);

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
  const getTagColor = useCallback((tag: string): string => {
    if (TAG_COLOR_MAP[tag.toLowerCase()]) {
      return TAG_COLOR_MAP[tag.toLowerCase()];
    }
    let hash = 0;
    for (let i = 0; i < tag.length; i++) {
      hash = tag.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = hash % 360;
    return `hsl(${hue}, 35%, 55%)`;
  }, []);

  const getNodeColor = useCallback(
    (node: GraphNode): string => {
      if (!node.tags || node.tags.length === 0) {
        return "#94a3b8";
      }
      return getTagColor(node.tags[0]);
    },
    [getTagColor]
  );

  const allTags = useMemo((): Array<{ tag: string; count: number; color: string }> => {
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
  }, [graphData, getTagColor]);

  // Neighbor lookup built once per graph so hover/selection handlers are
  // O(degree) instead of rescanning every edge with O(E) filters
  const adjacency = useMemo(() => {
    const neighbors = new Map<string, Set<string>>();
    if (!graphData) return neighbors;
    graphData.nodes.forEach((node) => neighbors.set(node.id, new Set()));
    graphData.edges.forEach((edge) => {
      const sourceId = typeof edge.source === "string" ? edge.source : edge.source.id;
      const targetId = typeof edge.target === "string" ? edge.target : edge.target.id;
      neighbors.get(sourceId)?.add(targetId);
      neighbors.get(targetId)?.add(sourceId);
    });
    return neighbors;
  }, [graphData]);

  // D3 Force Simulation
  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    ilog("simulation effect: (re)building svg scene and handlers", {
      nodes: graphData.nodes.length,
      edges: graphData.edges.length,
    });
    const svg = select(svgRef.current);
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
    const simulation = forceSimulation<GraphNode>(nodes)
      .force("charge", forceManyBody<GraphNode>().strength(-300).distanceMin(20).distanceMax(400))
      .force("center", forceCenter(width / 2, height / 2).strength(0.05))
      .force(
        "link",
        forceLink<GraphNode, GraphEdge>(edges)
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
        forceCollide<GraphNode>()
          .radius((d) => (d.radius || 10) + 5)
          .strength(0.5)
          .iterations(1)
      )
      .alphaDecay(0.03)
      .velocityDecay(0.4);

    // Soft boundary constraint as a proper force so it also applies during
    // the synchronous pre-settle below (event handlers only run on live ticks)
    simulation.force("boundary", () => {
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
    });

    // Settle most of the layout synchronously (a few ms of CPU) so the page
    // never shows the chaotic cold-start swirl, but keep some residual
    // energy — restarted below — so the graph breathes into its final
    // positions for a couple of seconds instead of loading as a still image
    const SETTLE_TO_ALPHA = 0.3;
    simulation.stop();
    while (simulation.alpha() > SETTLE_TO_ALPHA) simulation.tick();

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
      .style("fill", "var(--color-text-primary)")
      .style("paint-order", "stroke")
      .style("stroke", "var(--color-surface-default)")
      .style("stroke-width", "4px")
      .style("stroke-linejoin", "round")
      .style("opacity", 0)
      .style("pointer-events", "none")
      .text((d) => d.title || d.id);

    // Reset to selected state
    function resetToSelectedState() {
      const currentSelectedId = selectedNodeIdRef.current;
      if (!currentSelectedId) return;

      const connectedIds = adjacency.get(currentSelectedId) ?? EMPTY_SET;

      nodeElements
        .attr("opacity", (d) => {
          if (d.id === currentSelectedId) return 1.0;
          if (connectedIds.has(d.id)) return 1.0;
          return 0.35;
        })
        .attr("r", (d) => {
          if (d.id === currentSelectedId) return (d.radius || 10) * 1.4;
          return d.radius || 10;
        })
        .attr("stroke", (d) => (d.id === currentSelectedId ? "#D96D32" : "#374151"))
        .attr("stroke-width", (d) => (d.id === currentSelectedId ? 4 : 1))
        .attr("filter", null);

      linkElements
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
          return isConnected ? "#D96D32" : "#9ca3af";
        });

      labelElements
        .style("opacity", (d) => {
          if (d.id === currentSelectedId) return 1.0;
          if (connectedIds.has(d.id)) return 0.75;
          return 0;
        })
        .style("font-weight", (d) => (d.id === currentSelectedId ? "700" : "500"))
        .style("font-size", (d) => (d.id === currentSelectedId ? "15px" : "13px"));
    }

    // Reset to default state
    function resetToDefault() {
      nodeElements
        .attr("opacity", 1.0)
        .attr("r", (d) => d.radius || 10)
        .attr("stroke", "#374151")
        .attr("stroke-width", 1)
        .attr("filter", null);

      linkElements.attr("stroke-opacity", 0.4).attr("stroke-width", 1).attr("stroke", "#9ca3af");

      labelElements.style("opacity", 0);
    }

    // Hover handlers. Styling is applied directly (no d3 transitions) with
    // CSS transitions in the stylesheet doing the animation — mousing across
    // the graph fires enter/leave storms, and spawning JS interpolators for
    // every node/link/label on each one is what made hover laggy
    let lastRaisedId: string | null = null;
    function handleNodeHover(_event: MouseEvent, hoveredNode: GraphNode) {
      const connectedIds = adjacency.get(hoveredNode.id) ?? EMPTY_SET;

      // Bring hovered cluster to front — DEFERRED out of event dispatch.
      // appendChild removes+reinserts the element; if that happens inside
      // the mouseenter that Chrome fires between pointerdown and its
      // compatibility mousedown, Chrome retargets the mousedown to the
      // parent <g> and every circle-level handler goes deaf (#208).
      // Raise only once per hovered node: in real Chrome (not headless),
      // reinserting the element under the cursor refires boundary events,
      // and re-raising on each of those keeps the DOM churning (#210)
      if (lastRaisedId !== hoveredNode.id) {
        lastRaisedId = hoveredNode.id;
        requestAnimationFrame(() => {
          nodeElements.each(function (d) {
            if (d.id === hoveredNode.id || connectedIds.has(d.id)) {
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
        });
      }

      // Visual highlighting - nodes
      nodeElements
        .attr("opacity", (d) => {
          if (d.id === hoveredNode.id) return 1.0;
          if (connectedIds.has(d.id)) return 1.0;
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
          return isConnected ? "#E8773C" : "#9ca3af";
        });

      // Show labels for hovered cluster
      labelElements
        .style("opacity", (d) => {
          if (d.id === hoveredNode.id) return 1.0;
          if (connectedIds.has(d.id)) return 0.85;
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

    function handleNodeClick(event: MouseEvent) {
      ilog("node click fired", { defaultPrevented: event.defaultPrevented });
      // Selection happens on mousedown (drag start); this handler only
      // shields the svg background-deselect handler from the bubbled click
      event.stopPropagation();
    }

    // Attach event handlers. Selection AND open-note both ride on
    // pointerdown: unlike the compatibility mousedown/click/dblclick
    // pipeline, it is dispatched before any of our handlers can perturb the
    // DOM and cannot be suppressed or retargeted upstream. The native
    // dblclick event needs mousedown+click to land on the same circle twice,
    // and Chrome retargets that pipeline after DOM reorders (#208) — which
    // is why dblclick-to-open never fired in real Chrome (#210). Two
    // pointerdowns on the same node within the window are immune.
    const DOUBLE_PRESS_MS = 400;
    let lastPress: { id: string; time: number } | null = null;

    nodeElements
      .on("pointerdown.select", (event: PointerEvent, d: GraphNode) => {
        if (event.button !== 0) return;
        if (
          lastPress &&
          lastPress.id === d.id &&
          event.timeStamp - lastPress.time < DOUBLE_PRESS_MS
        ) {
          ilog("double press -> navigating", { id: d.id });
          lastPress = null;
          router.push(`/knowledge-base/notes/${d.id}`);
          return;
        }
        lastPress = { id: d.id, time: event.timeStamp };
        ilog("pointerdown -> selecting node", { id: d.id });
        setSelectedNode(d);
        clearNodeParam();
      })
      .on("mouseenter", handleNodeHover)
      .on("mouseleave", handleNodeLeave)
      .on("click", handleNodeClick);

    // Enable dragging. A human click wobbles 1-2px, which fires d3's "drag"
    // — if that reheats the simulation, the node drifts on mouseup and the
    // second click of a double-click misses it. So nothing reheats or moves
    // until the pointer travels past the same 10px click distance.
    let dragOrigin: [number, number] | null = null;
    let dragEngaged = false;

    const drag = d3Drag<SVGCircleElement, GraphNode>()
      // Tolerate small pointer movement so clicks/double-clicks aren't
      // swallowed as micro-drags (default clickDistance is 0)
      .clickDistance(10)
      .on("start", (event, d) => {
        ilog("drag start", { id: d.id });
        dragOrigin = [event.x, event.y];
        dragEngaged = false;
        // Pin the node but don't reheat the simulation yet
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        if (!dragEngaged) {
          if (dragOrigin && Math.hypot(event.x - dragOrigin[0], event.y - dragOrigin[1]) < 10) {
            return;
          }
          dragEngaged = true;
          // A real drag is not the first half of a double press
          lastPress = null;
        }
        simulation.alphaTarget(0.3).restart();
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
        selection: Selection<BaseType | SVGCircleElement, GraphNode, SVGGElement, unknown>
      ) => void
    );

    // Update element positions from simulation state
    function ticked() {
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
    }

    // Paint the pre-settled layout immediately, then let the residual
    // energy play out as a brief live settle
    ticked();
    simulation.on("tick", ticked);
    simulation.restart();

    // Click anywhere in the graph that isn't a node (background, edges,
    // labels) to deselect. Node clicks stopPropagation so they never land here.
    svg.on("click", (event) => {
      ilog("svg background click -> deselect", { target: (event.target as Element).tagName });
      setSelectedNode(null);
      clearNodeParam();
    });

    // Diagnostic probe: logs what hit-testing sees for EVERY press inside
    // the svg, plus where the nearest data node believes it is. If target
    // is "svg" while nearestDistance <= nearestRadius, hit-testing is
    // broken (pointer-events); if nearestDistance is large, the visible
    // scene does not match this instance's data (zombie scene).
    svg.on("pointerdown.diag", (event: PointerEvent) => {
      const [mx, my] = pointer(event, svg.node());
      let nearest: GraphNode | null = null;
      let best = Infinity;
      for (const n of nodes) {
        const dist = Math.hypot((n.x ?? 0) - mx, (n.y ?? 0) - my);
        if (dist < best) {
          best = dist;
          nearest = n;
        }
      }
      ilog("pointerdown probe", {
        target: (event.target as Element).tagName,
        graphXY: [Math.round(mx), Math.round(my)],
        nearestNode: nearest?.id,
        nearestDistance: Math.round(best),
        nearestRadius: nearest?.radius,
        hitTest: document.elementFromPoint(event.clientX, event.clientY)?.tagName,
        svgScenesInDocument: document.querySelectorAll("svg[role='img']").length,
        circlesInDocument: document.querySelectorAll("svg[role='img'] circle").length,
        // If defaultPrevented is true here, something (likely an extension
        // content script) canceled pointerdown — the browser then suppresses
        // the compatibility mousedown/click that d3's handlers rely on
        defaultPrevented: event.defaultPrevented,
        button: event.button,
        buttons: event.buttons,
        ctrlKey: event.ctrlKey,
        pointerType: event.pointerType,
        isTrusted: event.isTrusted,
      });
    });

    // Trace the mouse-event chain: if the window capture probe fires but
    // the svg one doesn't, something stopped propagation in between
    svg.on("mousedown.diag", (event: MouseEvent) => {
      ilog("mousedown reached svg", {
        target: (event.target as Element).tagName,
        button: event.button,
        defaultPrevented: event.defaultPrevented,
      });
    });
    svg.on("click.diag", (event: MouseEvent) => {
      ilog("click reached svg", {
        target: (event.target as Element).tagName,
        defaultPrevented: event.defaultPrevented,
      });
    });
    const windowMousedownProbe = (event: MouseEvent) => {
      if ((event.target as Element | null)?.closest?.("svg[role='img']")) {
        ilog("mousedown at window capture", {
          target: (event.target as Element).tagName,
          button: event.button,
          defaultPrevented: event.defaultPrevented,
        });
      }
    };
    window.addEventListener("mousedown", windowMousedownProbe, true);

    ilog("scene built", {
      circlesInThisScene: nodeElements.size(),
      circlesInDocument: document.querySelectorAll("svg[role='img'] circle").length,
      svgScenesInDocument: document.querySelectorAll("svg[role='img']").length,
    });

    // Cleanup: stop the sim AND remove this instance's scene + handlers so
    // an unmounting instance can never leave a visible-but-dead graph behind
    return () => {
      ilog("simulation effect cleanup: tearing down scene");
      simulation.stop();
      window.removeEventListener("mousedown", windowMousedownProbe, true);
      svg
        .on("click", null)
        .on("pointerdown.diag", null)
        .on("mousedown.diag", null)
        .on("click.diag", null);
      svg.selectAll("*").remove();
    };
  }, [graphData, adjacency, getNodeColor, router, clearNodeParam, ilog]);

  // Separate effect for visual updates (selection, filters) without recreating simulation
  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    const svg = select(svgRef.current);
    const nodeElements = svg.selectAll<SVGCircleElement, GraphNode>("circle");
    const linkElements = svg.selectAll<SVGLineElement, GraphEdge>("line");
    const labelElements = svg.selectAll<SVGTextElement, GraphNode>("text");

    if (nodeElements.empty()) return;

    const selectedNodeId = selectedNode?.id || null;
    ilog("selection state applied", { selectedNodeId });
    const selectedTagsArray = Array.from(selectedTags);
    const isFiltering = selectedTags.size > 0;

    // Apply selection state
    if (selectedNodeId) {
      const connectedIds = adjacency.get(selectedNodeId) ?? EMPTY_SET;

      nodeElements
        .attr("opacity", (d) => {
          if (d.id === selectedNodeId) return 1.0;
          if (connectedIds.has(d.id)) return 1.0;
          return 0.35;
        })
        .attr("r", (d) => {
          if (d.id === selectedNodeId) return (d.radius || 10) * 1.4;
          return d.radius || 10;
        })
        .attr("stroke", (d) => (d.id === selectedNodeId ? "#D96D32" : "#374151"))
        .attr("stroke-width", (d) => (d.id === selectedNodeId ? 4 : 1))
        .attr("filter", null);

      linkElements
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
          return isConnected ? "#D96D32" : "#9ca3af";
        });

      labelElements
        .style("opacity", (d) => {
          if (d.id === selectedNodeId) return 1.0;
          if (connectedIds.has(d.id)) return 0.75;
          return 0;
        })
        .style("font-weight", (d) => (d.id === selectedNodeId ? "700" : "500"))
        .style("font-size", (d) => (d.id === selectedNodeId ? "15px" : "13px"));
    } else if (isFiltering) {
      // Apply tag filtering
      nodeElements
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
            return "#D96D32";
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

      linkElements.attr("stroke-opacity", (d) => {
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

      labelElements.style("opacity", 0);
    } else {
      // Reset to default
      nodeElements
        .attr("opacity", 1.0)
        .attr("r", (d) => d.radius || 10)
        .attr("stroke", "#374151")
        .attr("stroke-width", 1)
        .attr("filter", null);

      linkElements.attr("stroke-opacity", 0.4).attr("stroke-width", 1).attr("stroke", "#9ca3af");

      labelElements.style("opacity", 0);
    }
  }, [selectedNode, selectedTags, filterLogic, graphData, adjacency, ilog]);

  if (loading) {
    return (
      <div className={styles.container}>
        <LoadingState variant="graph" label="Loading graph" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <ErrorState message={error} backHref="/knowledge-base/notes" backLabel="← Back to notes" />
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className={styles.container}>
        <EmptyState
          message="No notes to visualize yet. Create some notes to see the graph!"
          actionLabel="Create your first note"
          actionHref="/knowledge-base/notes/new"
          backHref="/knowledge-base/notes"
          backLabel="← Back to notes"
        />
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
              role="img"
              aria-label={`Interactive graph visualization showing ${graphData.count.nodes} notes and ${graphData.count.edges} connections. Use mouse to hover, click, and drag nodes.`}
            />
            <div className={styles.instructions}>
              Click a node to select it · Double-click to open the note · Click the background to
              deselect · Drag to reposition · Larger nodes = hub notes with more links
            </div>
          </div>

          {/* Sidebar - Right column */}
          <div className={styles.sidebar}>
            {/* Selected node details */}
            {selectedNode && (
              <div className={styles.selectedNodePanel}>
                <h3 className={styles.nodeTitle}>
                  <Link
                    href={`/knowledge-base/notes/${selectedNode.id}`}
                    aria-label={`View note: ${selectedNode.title || selectedNode.id}`}
                  >
                    {selectedNode.title}
                  </Link>
                </h3>
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
              </div>
            )}

            {/* Tag filters */}
            <div className={styles.filterSection}>
              <div className={styles.filterControls}>
                <h4 className={styles.filterTitle}>Filter by tag</h4>
                <div className={styles.filterLogic} role="group" aria-label="Tag filter logic">
                  <button
                    className={filterLogic === "OR" ? styles.active : ""}
                    onClick={() => setFilterLogic("OR")}
                    aria-label="Match any selected tag"
                    aria-pressed={filterLogic === "OR"}
                  >
                    Any
                  </button>
                  <button
                    className={filterLogic === "AND" ? styles.active : ""}
                    onClick={() => setFilterLogic("AND")}
                    aria-label="Match all selected tags"
                    aria-pressed={filterLogic === "AND"}
                  >
                    All
                  </button>
                </div>
              </div>
              <div className={styles.tagList} role="group" aria-label="Filter tags">
                {allTags.map(({ tag, count, color }) => {
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
                      aria-label={`Filter by tag: ${tag}, ${count} notes`}
                      aria-pressed={isActive}
                    >
                      <span
                        className={styles.tagDot}
                        style={{ backgroundColor: color }}
                        aria-hidden="true"
                      />
                      <span className={styles.tagName}>{tag}</span>
                      <span className={styles.tagCount}>({count})</span>
                    </button>
                  );
                })}
              </div>
              {selectedTags.size > 0 && (
                <div className={styles.filterActions}>
                  <button
                    onClick={() => setSelectedTags(new Set())}
                    className={styles.clearButton}
                    aria-label="Clear all tag filters"
                  >
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
