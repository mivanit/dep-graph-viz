def generate_html(dot_file_path: str, output_html_path: str):
    dot_content: str = ""
    with open(dot_file_path, 'r') as dot_file:
        dot_content = dot_file.read()
        
    dot_content = dot_content.replace('`', '\\`')

    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Graphviz with Interactive Features</title>
    <script src="https://d3js.org/d3.v5.min.js"></script>
    <script src="https://unpkg.com/@hpcc-js/wasm@0.3.13/dist/index.min.js"></script>
    <script src="https://unpkg.com/d3-graphviz@3.1.0/build/d3-graphviz.min.js"></script>
    <style>
        .node { cursor: pointer; }
        .active { stroke-width: 3px; }
        .highlighted { stroke-width: 4px; stroke: red; }
        .bold { font-weight: bold; }
    </style>
</head>
<body>
    <div id="graph" style="width: 100%; height: 100vh;"></div>
    <script>
        const dot = `$$DOT_CONTENT$$`;

        d3.select("#graph").graphviz()
            .renderDot(dot)
            .on("end", function() {
                d3.selectAll('.node')
                    .call(d3.drag()
                        .on('start', dragstarted)
                        .on('drag', dragged)
                        .on('end', dragended))
                    .on('mouseover', mouseover)
                    .on('mouseout', mouseout);
            });

        function dragstarted(event, d) {
            d3.select(this).raise().classed('active', true);
        }

        function dragged(event, d) {
            const node = d3.select(this);
            const transform = node.attr('transform');
            const translate = transform.match(/translate\\(([^)]+)\\)/)[1].split(',');
            const dx = event.x - parseFloat(translate[0]);
            const dy = event.y - parseFloat(translate[1]);

            node.attr('transform', `translate(${event.x},${event.y})`);

            // Update connected edges
            d3.selectAll('.edge path').each(function() {
                const path = d3.select(this);
                const edgeData = path.attr('d').match(/M(-?\\d+),(-?\\d+)C(-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+)/);
                if (edgeData) {
                    const [_, x1, y1, cx1, cy1, cx2, cy2, x2, y2] = edgeData.map(Number);

                    if (path.attr('id').includes(node.attr('id'))) {
                        if (x1 === d.x && y1 === d.y) {
                            path.attr('d', `M${event.x},${event.y}C${event.x + (cx1 - x1)},${event.y + (cy1 - y1)},${cx2},${cy2},${x2},${y2}`);
                        } else if (x2 === d.x && y2 === d.y) {
                            path.attr('d', `M${x1},${y1}C${cx1},${cy1},${event.x + (cx2 - x2)},${event.y + (cy2 - y2)},${event.x},${event.y}`);
                        }
                    }
                }
            });
        }

        function dragended(event, d) {
            d3.select(this).classed('active', false);
        }

        function mouseover(event, d) {
            const nodeId = d3.select(this).attr('id');
            d3.select(this).select('text').classed('bold', true);
            d3.selectAll('.edge path').each(function() {
                const path = d3.select(this);
                if (path.attr('id').includes(nodeId)) {
                    path.classed('highlighted', true);
                }
            });
        }

        function mouseout(event, d) {
            d3.select(this).select('text').classed('bold', false);
            d3.selectAll('.edge path').classed('highlighted', false);
        }

        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", function(event) {
                d3.select('#graph g').attr("transform", event.transform);
            });

        d3.select('#graph').call(zoom);

    </script>
</body>
</html>
"""
    html_content = html_content.replace("$$DOT_CONTENT$$", dot_content)
    
    with open(output_html_path, 'w') as output_file:
        output_file.write(html_content)