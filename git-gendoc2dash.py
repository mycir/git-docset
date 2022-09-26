"""
    Generate Dash docset for Git
    http://git-scm.com/docs
"""
import itertools
import os
import sqlite3
from shutil import copy

import requests
from bs4 import BeautifulSoup as bs


def initialise():
    global docset_name
    global output
    global root_url
    global parser
    global db
    global cur
    global sections
    docset_name = "Git.docset"
    output = docset_name + "/Contents/Resources/Documents"
    root_url = "http://git-scm.com/docs"
    parser = "html.parser"
    docpath = output + "/"
    if not os.path.exists(docpath):
        os.makedirs(docpath)
    copy("Git-Icon-1788C.png", f"{docset_name}/icon.png")
    db = sqlite3.connect(docset_name + "/Contents/Resources/docSet.dsidx")
    cur = db.cursor()
    try:
        cur.execute("DROP TABLE searchIndex;")
    except Exception:
        pass
    cur.execute(
        "CREATE TABLE searchIndex( \
            id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
    )
    cur.execute("CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);")
    sections = {"index.html": ("Git - Reference", "Index")}


def get_index(url):
    page = requests.get(url).text
    soup = bs(page, parser)
    title = soup.find("title")
    doc_soup = soup.find(id="main")
    doc_soup.insert(0, title)
    fix_links(doc_soup)
    with open(
        os.path.join(output, "index.html"),
        "w",
        encoding="iso-8859-1",
        errors="ignore",
    ) as f:
        f.write(str(doc_soup))


def update_db(sections):
    for path, (name, type) in sections.items():
        if type == "":
            if name[0].isupper():
                type = "Guide"
            else:
                type = "func"
        cur.execute(
            "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)",
            (name, type, path),
        )
        print("DB add >> name: %s, path: %s" % (name, path))


def add_docs(start, end):
    global sections
    start_prev = len(sections) - 1
    for path, (name, _) in dict(
        itertools.islice(sections.items(), start, end)
    ).items():
        # create subdir
        folder = os.path.join(output)
        for i in range(0, len(path.split("/")) - 1):
            folder += "/" + path.split("/")[i]
        if not os.path.exists(folder):
            os.makedirs(folder)
        if "#" not in path:
            try:
                page_id = path.split("/")[-1]
                url = root_url + "/" + page_id
                print(f"Downloading document: {page_id} - {name}")
                page = requests.get(url).text
                soup = bs(page, parser)
                doc_soup = soup.find(id="main")
                title_tag = soup.new_tag("title")
                title_tag.append(name)
                doc_soup.insert(0, title_tag)
                doc_soup = fix_links(doc_soup)
                with open(
                    os.path.join(folder, page_id),
                    "w",
                    encoding="iso-8859-1",
                    errors="ignore",
                ) as f:
                    f.write(str(doc_soup))
                print("Success")
            except Exception as e:
                print("Failed")
                print("{}: {}".format(type(e).__name__, e))
    start = end + 1
    end = len(sections) - 1
    if end > start_prev:
        add_docs(start, end)


def fix_links(doc_soup):
    global sections
    for link in doc_soup.findAll("a", {"href": True}):
        if link.attrs and not link["href"].startswith("http"):
            if "#" not in link.attrs["href"]:
                type = ""
                if link.text.endswith("[1]"):
                    type = "Command"
                elif link.text.endswith("[5]"):
                    type = "File"
                elif link.text.endswith("[7]"):
                    type = "Guide"
                path = link["href"][1:] + ".html"
                link["href"] = f"/git{link['href']}.html"
                if path not in sections:
                    sections.update({path: (link.text.strip(), type)})
            else:
                link_parts = link["href"].split("#")
                if link_parts[0] != "":
                    link[
                        "href"
                    ] = f"/git{link_parts[0]}.html#{link_parts[1]}"
    return doc_soup


def add_info_plist():
    name = docset_name.split(".")[0]
    info = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"'
        ' "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "    <key>CFBundleIdentifier</key>\n"
        "    <string>{0}</string>\n"
        "    <key>CFBundleName</key>\n"
        "    <string>{1}</string>\n"
        "    <key>DocSetPlatformFamily</key>\n"
        "    <string>{2}</string>\n"
        "    <key>isDashDocset</key>\n"
        "    <true/>\n"
        "    <key>dashIndexFilePath</key>\n"
        "    <string>index.html</string>\n"
        "</dict>\n"
        "</plist>\n".format(name.lower(), name, name.lower())
    )
    with open(docset_name + "/Contents/Info.plist", "w") as f:
        f.write(info)


if __name__ == "__main__":
    initialise()
    get_index(root_url)
    add_docs(1, len(sections) - 1)
    add_info_plist()
    update_db(sections)
    db.commit()
    db.close()
