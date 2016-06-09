from htmlmash import Element, html, head, meta, title, script, body, div, p

document = Element(doctype="html")

if "scripts" not in globals():
    scripts = ["script_one.js", "script_two.js", "script_three.js"]
if "paragraphs" not in globals():
    paragraphs = ["one", "two", "three"]

with html() as html_element:
    document.append(html_element)

    with head() as head_element:
        html_element.append(head_element)

        head_element.append(meta(charset="UTF-8"))
        head_element.append(title("Simple Page"))
        head_element.append([script(js) for js in scripts])

    with body() as body_element:
        html_element.append(body_element)

        with div() as div_element:
            body_element.append(div_element)

            div_element.append(lambda: (p(paragraph) for paragraph in paragraphs))
