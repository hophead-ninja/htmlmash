# htmlmash
Objective html template engine. API is under construction and may be unstable.

### Abstract
Htmlmash provides tools to loading and processing pythonic html templates.
Templates are interpreted as a typical python modules/packages. They have python syntax and are subject to the same mechanism as conventional modules.
The difference is in code execution and in methods of interpretation of expressions and some statements.

### Description
###### Module
The core of htmlmash module is the `Element`. It's similar to `xml.etree.ElementTree.Element`. Element have tag, attributes, text, tail and may contain other elements or functions without arguments.
Module have dynamic, lazy element builder, generated when module attribute is not found. Instead `from htmlmash import Element; element = Element("ul")` 
you can write `from htmlmash import ul; element = ul()`. Serialization is done using string conversion `str(element)`, if subelement is a function the result is serializing.
###### Templates
Template module is a .hpy file with python syntax, but it is a little bit differently interpreted.
- value of expression without assign is a template node (new element, or element`s text)
- conditions and loops statements are executed during template serialization
- globals are assigns when the identifier name is not already assigned (for instancing)
- template module can be instanced
- template module can be a package
 
###### Sample
`simple_page.hpy`
```python
__doctype__ = "html"

scripts = ["script_one.js", "script_two.js", "script_three.js"]
paragraphs = ["one", "two", "three"]

with html():
    with head():
        meta(charset="UTF-8")
        title("Simple Page")
        [script(js) for js in scripts]

    with body():
        with div(class_="container"):
            (p(paragraph) for paragraph in paragraphs)
```
Terminal:
```
$ python3 -m htmlmash simple_page.hpy >> simple_page.html
```
`simple_page.html` formatted to improve sample readability:
```
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>Simple Page</title>
        <script>script_one.js</script>
        <script>script_two.js</script>
        <script>script_three.js</script>
    </head>
    <body>
        <div class="container">
            <p>one</p>
            <p>two</p>
            <p>three</p>
        </div>
    </body>
</html>
```
Pure python version generated during template loading:
```python
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
```
### Usage
#### Simple
Template `simple_template.hpy`
```python
text = "a template."
"This is {}\n".format(text)
```
Console:
```python
>>> import htmlmash
>>> import simple_template
>>> print(simple_template)
This is a template.
>>> simple_template.text = "an objective template"
>>> print(simple_template)
This is an objective template
>>> instance = simple_template(text="an instance")
>>> print(instance)
This is an instance
```
#### Scopes
```python
# template scope

text = "a template."

# dynamic expression
"This is {}\n".format(text)

# static expression
"This is " + text + "\n"

def static_text():
    # python scope
    "regular", "python scope",
    "these three texts are not included in the template"

    # but you can return something
    return "This is {}\n".format(text)
# back to template scope
static_text()  # and add returned text to template

def mixed_text():
    # python scope
    with Element() as dynamic_text:
        # (sub)template scope
        "This is {}\n".format(text)
    # python scope
    return "This is {} ".format(text), dynamic_text
# template scope
mixed_text()
```
Console:
```python
>>> print(simple_template)
This is a template.
This is a template.
This is a template.
This is a template. This is a template.
>>> simple_template.text = "an objective template"
>>> print(simple_template)
This is an objective template
This is a template.
This is a template.
This is a template. This is an objective template
```
#### Package sample
`page/__init__.hpy`
```python
from page import menu, articles, contact

__doctype__ = "html"

page_id = "main"

with html():
    with head():
        meta(charset="UTF-8")
        title("Page")

    with body():
        header_text = "Page"
        header(h1(header_text) if page_id == "main" else span(header_text))
        menu(items=menu.items+[("Contact", "contact.html")])
        with div(class_="container"):
            if page_id == "main":
                p("Welcome")
            elif page_id == "blog":
                section(articles, class_="page-articles")
            elif page_id == "contact":
                contact
```
`page/menu.hpy`
```python
items = [("Page", "index.html"), ("Blog", "blog.html")]

nav(ul([li(a(name, href=location), class_="menu-item") for name, location in items], class_="menu"))
```
`page/articles.hpy`
```python
from collections import namedtuple
Article = namedtuple('Article', ['title', 'text'])

news = [Article("First Article", "Text here"), Article("Second Article", "Text here again")]

if news:
    for idx, post in enumerate(news):
        article(h1(post.title), p(post.text), class_="artcile-{}".format(idx))
else:
    div("no articles")
```
`page/contact.hpy`
```python
with form(action=""):
    label("Name: ",  for_="name"), br(), input_(id="name", name="Name", type="text", size="30"), br()
    label("Email: "), br(), input_(id="email", name="email", type="email", size="30"), br()
    label("Message: "), br(), textarea(id="message", name="message", rows="7", cols="30"), br()
```
`site_builder.py`
```python
import htmlmash
import page

if __name__ == "__main__":
    with open("build/index.html", 'w') as f:
        f.write(str(page))

    page.page_id = "blog"
    # uncomment below line to clear articles
    # page.articles.clear()
    with open("build/blog.html", 'w') as f:
        f.write(str(page))

    page.page_id = "contact"
    with open("build/contact.html", 'w') as f:
        f.write(str(page))
```
Terminal:
```
$ mkdir build
$ python3 site_builder.py
```