import React, { useRef, useEffect, useState } from "react";
import "./Graph.css";
import * as d3 from "d3";
import { nodes as initialNodes } from "./nodesConfig";

function GraphVisualize() {
  const [links, setLinks] = useState([]);
  const nodes = initialNodes;
  const svgRef = useRef(null);

  const generateAllPairs = (nodes) => {
    const pairs = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        pairs.push({
          source: nodes[i].id,
          target: nodes[j].id,
        });
      }
    }
    return pairs;
  };

  useEffect(() => {
    const newLinks = generateAllPairs(nodes);
    setLinks(newLinks);
  }, [nodes]);

  useEffect(() => {
    if (!svgRef.current) return;

    const width = 800;
    const height = 600;

    const svg = d3
      .select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    svg.selectAll("*").remove();

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(links)
          .id((d) => d.id)
          .distance(250)
      )
      .force("charge", d3.forceManyBody().strength(-500))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#ffffff")
      .attr("stroke-opacity", 1)
      .attr("stroke-width", 2);

    const node = svg
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 20)
      .attr("fill", "#69b3a2");

    const labels = svg
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => d.id)
      .attr("font-size", "12px")
      .attr("dx", 25)
      .attr("dy", 4);

    const drag = d3
      .drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);

    node.call(drag);

    function dragstarted(event) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);

      labels.attr("x", (d) => d.x).attr("y", (d) => d.y);
    });
  }, [nodes, links]);

  return (
    <div className="graphContainer">
      <svg ref={svgRef}></svg>
    </div>
  );
}

export default GraphVisualize;
