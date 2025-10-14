"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { AuthStatusIndicator } from "@/components/AuthStatusBanner";
import { logger } from "@/lib/logger";

interface GraphNode {
  id: string;
  title: string;
  author: string;
  is_ephemeral: boolean;
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

        // Initialize node positions randomly
        data.nodes = data.nodes.map((node) => ({
          ...node,
          x: Math.random() * 800,
          y: Math.random() * 600,
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

  // Simple force simulation
  useEffect(() => {
    if (!graphData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const nodes = graphData.nodes;
    const edges = graphData.edges;

    function animate() {
      if (!ctx) return;

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Apply forces
      const alpha = 0.1;

      // Repulsion between nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x! - nodes[i].x!;
          const dy = nodes[j].y! - nodes[i].y!;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 100 / (dist * dist);

          nodes[i].vx = nodes[i].vx! - force * dx * alpha;
          nodes[i].vy = nodes[i].vy! - force * dy * alpha;
          nodes[j].vx = nodes[j].vx! + force * dx * alpha;
          nodes[j].vy = nodes[j].vy! + force * dy * alpha;
        }
      }

      // Attraction along edges
      edges.forEach((edge) => {
        const source = nodes.find((n) => n.id === edge.source);
        const target = nodes.find((n) => n.id === edge.target);
        if (!source || !target) return;

        const dx = target.x! - source.x!;
        const dy = target.y! - source.y!;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * 0.01;

        source.vx = source.vx! + force * dx * alpha;
        source.vy = source.vy! + force * dy * alpha;
        target.vx = target.vx! - force * dx * alpha;
        target.vy = target.vy! - force * dy * alpha;
      });

      // Center force
      const centerX = width / 2;
      const centerY = height / 2;
      nodes.forEach((node) => {
        const dx = centerX - node.x!;
        const dy = centerY - node.y!;
        node.vx = node.vx! + dx * 0.01 * alpha;
        node.vy = node.vy! + dy * 0.01 * alpha;
      });

      // Update positions and apply damping
      nodes.forEach((node) => {
        node.vx = node.vx! * 0.92; // Increased from 0.85 for slower movement
        node.vy = node.vy! * 0.92;
        node.x = node.x! + node.vx!;
        node.y = node.y! + node.vy!;

        // Keep nodes within bounds
        node.x = Math.max(30, Math.min(width - 30, node.x));
        node.y = Math.max(30, Math.min(height - 30, node.y));
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
        ctx.fillStyle = node.is_ephemeral ? "#fbbf24" : "#3b82f6";
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
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="mb-4 h-8 w-1/3 rounded bg-gray-200"></div>
          <div className="h-96 rounded bg-gray-200"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h2 className="mb-2 font-semibold text-red-800">Error</h2>
          <p className="text-red-600">{error}</p>
          <Link
            href="/knowledge-base/notes"
            className="mt-4 inline-block text-blue-600 hover:underline"
          >
            ← Back to notes
          </Link>
        </div>
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <AuthStatusIndicator />
        <div className="mb-6">
          <Link href="/knowledge-base/notes" className="text-sm text-blue-600 hover:underline">
            ← Back to notes
          </Link>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-gray-600">
            No notes to visualize yet. Create some notes to see the graph!
          </p>
          <Link
            href="/knowledge-base/notes/new"
            className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          >
            Create your first note
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AuthStatusIndicator />

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="mb-4 flex gap-4">
            <Link href="/knowledge-base" className="text-sm text-blue-600 hover:underline">
              ← Knowledge Base
            </Link>
            <Link href="/knowledge-base/notes" className="text-sm text-blue-600 hover:underline">
              All notes
            </Link>
          </div>

          <h1 className="mb-2 text-3xl font-bold text-gray-900">Notes Graph</h1>
          <p className="text-gray-600">
            {graphData.count.nodes} notes · {graphData.count.edges} connections
          </p>
        </div>

        {/* Graph visualization */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <canvas
            ref={canvasRef}
            width={1200}
            height={700}
            onClick={handleCanvasClick}
            onMouseMove={handleCanvasMouseMove}
            className="w-full"
          />

          <div className="mt-4 flex items-center gap-6 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-blue-600"></div>
              <span>Persistent notes</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-yellow-400"></div>
              <span>Ephemeral notes</span>
            </div>
            <div className="ml-auto text-gray-500">Click a node to select · Hover to see title</div>
          </div>
        </div>

        {/* Selected node details */}
        {selectedNode && (
          <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <h3 className="mb-2 font-semibold text-blue-900">{selectedNode.title}</h3>
            <div className="mb-3 flex items-center gap-4 text-sm text-blue-700">
              <code className="rounded bg-blue-100 px-2 py-1">{selectedNode.id}</code>
              <span>by {selectedNode.author}</span>
              {selectedNode.is_ephemeral && (
                <span className="rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-800">
                  ephemeral
                </span>
              )}
            </div>
            {selectedNode.tags.length > 0 && (
              <div className="mb-3 flex gap-2">
                {selectedNode.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-blue-100 px-3 py-1 text-xs text-blue-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
            <div className="flex gap-3">
              <Link
                href={`/knowledge-base/notes/${selectedNode.id}`}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
              >
                View note
              </Link>
              <button
                onClick={() => setSelectedNode(null)}
                className="rounded-lg border border-blue-300 px-4 py-2 text-sm text-blue-700 hover:bg-blue-100"
              >
                Deselect
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
