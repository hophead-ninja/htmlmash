import htmlmash
import page

if __name__ == "__main__":
    with open("build/index.html", 'w') as f:
        f.write(str(page))

    page.page_id = "blog"
    # uncomment below line to clear articles
    # page.articles.news.clear()
    with open("build/blog.html", 'w') as f:
        f.write(str(page))

    page.page_id = "contact"
    with open("build/contact.html", 'w') as f:
        f.write(str(page))
