HTML_TEMPLATE: str = r"""
<!DOCTYPE html>
<html>
<head>
    <title>Static Graphviz SVG</title>
    <script src="https://d3js.org/d3.v5.min.js"></script>
    <script src="https://unpkg.com/@hpcc-js/wasm@0.3.13/dist/index.min.js"></script>
    <script src="https://unpkg.com/d3-graphviz@3.1.0/build/d3-graphviz.min.js"></script>
</head>
<body>
    <div id="graph" style="width: 100%; height: 100vh;"></div>
    <script>
        const dot = `$$DOT_CONTENT$$`;

        d3.select("#graph").graphviz()
            .renderDot(dot);
    </script>
</body>
</html>
"""

def generate_html(dot_file_path: str, output_html_path: str):
    dot_content: str = ""
    with open(dot_file_path, 'r') as dot_file:
        dot_content = dot_file.read()
        
    dot_content = dot_content.replace('`', '\\`')

    html_content: str = HTML_TEMPLATE.replace("$$DOT_CONTENT$$", dot_content)
    
    with open(output_html_path, 'w') as output_file:
        output_file.write(html_content)