"""
    Generate Dash docset for Git
    http://git-scm.com/docs
"""
import os
import sqlite3
import sys
from shutil import copy

import requests
from bs4 import BeautifulSoup as bs

# TODO analyse links for docs outside git-scm.com/docs branch and add these too


def initialise():
    global docset_name
    global output
    global root_url
    global parser
    global db
    global cur
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


def update_db(name, path):
    if name[0].isupper():
        type = "Guide"
    else:
        type = "func"
    cur.execute(
        "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)",
        (name, type, path),
    )
    print("DB add >> name: %s, path: %s" % (name, path))


def add_docs(doc_soup):
    sections = []
    titles = []
    for i, link in enumerate(doc_soup.findAll("a", {"href": True})):
        name = link.text.strip()
        path = link["href"]
        if path is not None and path.startswith("git/"):
            if "#" not in link["href"]:
                sections.append(path)
                titles.append(name)
    # download pages and update db
    for path, name in zip(sections, titles):
        # create subdir
        folder = os.path.join(output)
        for i in range(len(path.split("/")) - 1):
            folder += "/" + path.split("/")[i]
        if not os.path.exists(folder):
            os.makedirs(folder)
        if "#" not in path:
            try:
                page_id = path.split("/")[-1].split()[0]
                url = root_url + "/" + page_id
                print(f"Downloading document: {page_id} - {name}")
                page = requests.get(url).text
                soup = bs(page, parser)
                doc = soup.find(id="main")
                title_tag = soup.new_tag("title")
                title_tag.append(name)
                doc.insert(0, title_tag)
                with open(os.path.join(folder, page_id), "w") as f:
                    f.write(str(doc))
                print("Success")
                update_db(name, path)
            except Exception:
                print("Failed")


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


def fix_links(doc, strip, prefix="", suffix=""):
    for link in doc.findAll("a", {"href": True}):
        if link.attrs and "https" not in link["href"]:
            link["href"] = link["href"][1:]
            if "#" not in link.attrs["href"]:
                link["href"] = prefix + strip(link["href"]) + suffix
            else:
                link_parts = link["href"].split("#")
                link["href"] = (
                    "git" + strip(link_parts[0]) + suffix + "#" + link_parts[1]
                )
    return doc


def fix_links_in_all():
    for filename in os.listdir(output + "/git"):
        if filename != "git.html":
            print(f"Fixing links in {filename}")
            with open(f"{output}/git/{filename}", "r+") as f:
                soup = bs(f, parser)
                fix_links(
                    soup, lambda link: link.split("/")[-1], suffix=".html"
                )
                f.seek(0)
                f.truncate()
                f.write(str(soup))


def get_index(url, save_as):
    page = requests.get(url).text
    soup = bs(page, parser)
    title = soup.find("title")
    doc = soup.find(id="main")
    fix_links(doc, lambda link: link[4:], "git", ".html")
    doc.insert(0, title)
    with open(os.path.join(output, save_as), "w") as f:
        f.write(str(doc))
    return doc


if __name__ == "__main__":
    initialise()
    doc_soup = get_index(root_url, "index.html")
    add_docs(doc_soup)
    add_info_plist()
    with open(os.path.join(output, "git/git.html"), "r+") as f:
        soup = bs(f, parser)
        doc = fix_links(soup, lambda link: link[5:], suffix=".html")
        f.seek(0)
        f.truncate()
        f.write(str(doc))
    fix_links_in_all()
    db.commit()
    db.close()
    sys.exit(0)
