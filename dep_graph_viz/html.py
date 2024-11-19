import importlib.resources

import dep_graph_viz

HTML_TEMPLATE: str = importlib.resources.files(dep_graph_viz).joinpath("template.html").read_text()


def generate_html(dot_file_path: str, output_html_path: str):
    dot_content: str = ""
    with open(dot_file_path, "r") as dot_file:
        dot_content = dot_file.read()

    dot_content = dot_content.replace("`", "\\`")

    html_content: str = HTML_TEMPLATE.replace("$$DOT_CONTENT$$", dot_content)

    with open(output_html_path, "w") as output_file:
        output_file.write(html_content)
