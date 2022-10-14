"""
    Generate Dash docset for Git
    http://git-scm.com/docs
"""
import itertools
import os
import re
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
    output = f"{docset_name}/Contents/Resources/Documents"
    root_url = "http://git-scm.com/docs"
    parser = "html.parser"
    docpath = f"{output}/"
    if not os.path.exists(docpath):
        os.makedirs(docpath)
    copy("Git-Icon-1788C.png", f"{docset_name}/icon.png")
    db = sqlite3.connect(f"{docset_name}/Contents/Resources/docSet.dsidx")
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
    sections = {
        "index.html": ("Git - Reference", "Index"),
        "docs/git.html": ("git", "Command"),
    }


def get_git(url):
    global sections
    page = requests.get(url).text
    soup = bs(page, parser)
    title = soup.find("title")
    soup = soup.find(id="main")
    soup.insert(0, title)
    files = {"gitattributes", "gitignore", "gitmailmap", "gitmodules"}
    sects = {
        "_high_level_commands": "Command",
        "_low_level_commands": "Command",
        "_guides": "Guide",
        "_repository_command_and_file_interfaces": "Interface",
        "_file_formats_protocols_and_other_developer_interfaces": None,
    }
    pattern = str(list(sects.keys()))[3:-3].replace("', '", "|")
    headings = soup.findAll(
        "h2", {"id": re.compile(pattern, flags=re.IGNORECASE)}
    )
    types = list(sects.values())
    for i in range(0, len(sects)):
        dlists = headings[i].parent.findAll("div", attrs={"class": "dlist"})
        for dlist in dlists:
            links = dlist.findAll("a", {"class": False, "href": True})
            for link in links:
                path = link["href"].lstrip("/")
                if path.startswith("docs/git-"):
                    name = path.split("-", 1)[1]
                else:
                    name = path.replace("docs/", "")
                type = types[i]
                if type == "Interface":
                    if name in files:
                        type = "File"
                    elif name == "githooks":
                        type = "Hook"
                elif type is None:
                    if name.startswith("gitformat"):
                        type = "File"
                    elif name.startswith("gitprotocol"):
                        type = "Protocol"
                sections.update({f"{path}.html": (name, type)})
    fix_links(soup)
    folder = os.path.join(output, "docs")
    os.makedirs(folder, exist_ok=True)
    with open(
        os.path.join(output, "docs/git.html"),
        "w",
        encoding="iso-8859-1",
        errors="ignore",
    ) as f:
        f.write(str(soup))


def get_index(url):
    page = requests.get(url).text
    soup = bs(page, parser)
    title = soup.find("title")
    soup = soup.find(id="main")
    soup.insert(0, title)
    fix_links(soup, index=True)
    with open(
        os.path.join(output, "index.html"),
        "w",
        encoding="iso-8859-1",
        errors="ignore",
    ) as f:
        f.write(str(soup))


def add_docs(start, end):
    global sections
    start_prev = len(sections) - 1
    for path, (name, _) in dict(
        itertools.islice(sections.items(), start, end)
    ).items():
        folder = os.path.join(output)
        for i in range(0, len(path.split("/")) - 1):
            folder += f"/{path.split(f'/')[i]}"
        if not os.path.exists(folder):
            os.makedirs(folder)
        if "#" not in path:
            page_id = path.split("/")[-1]
            get_doc(page_id, fixlinks=True)
    start = end + 1
    end = len(sections) - 1
    if end > start_prev:
        add_docs(start, end)


def get_doc(
    page,
    url="http://git-scm.com/docs",
    ext="",
    type="",
    txt2html=False,
    fixlinks=False,
    update=False,
):
    global sections
    print(f"Downloading document: {page}")
    response = requests.get(f"{url}/{page}", stream=True)
    if response.status_code != 200:
        print(f"HTTP error: {response.status_code}")
        return
    if txt2html:
        doc = (
            f"<html><body><pre><title>{page.split('.')[0]}"
            f"</title>{response.text}</pre></body></html>"
        )
        page = page.split(".")[0]
    else:
        soup = bs(response.text, parser)
        title_tag = soup.new_tag("title")
        title_tag.append(page.split(".")[0])
        soup = soup.find(id="main")
        soup.insert(0, title_tag)
        if fixlinks:
            soup = fix_links(soup)
        doc = str(soup)
    with open(
        os.path.join(output, f"docs/{page}{ext}"),
        "w",
        encoding="iso-8859-1",
        errors="ignore",
    ) as f:
        f.write(doc)
        print("Success")
    if update:
        sections.update({f"docs/{page}{ext}": (page.rsplit("/")[0], type)})


def fix_links(soup, index=False):
    global sections
    for link in soup.findAll("a", {"href": True}):
        if link.attrs:
            p = re.compile("^http|mailto")
            if not re.match(p, link["href"]):
                if "#" not in link.attrs["href"]:
                    path_noext = link["href"].lstrip("/")
                    path = f"{path_noext}.html"
                    if index:
                        link["href"] = path
                    else:
                        if path not in sections:
                            if path_noext.startswith("docs/git-"):
                                name = path_noext.split("-", 1)[1]
                            else:
                                name = path_noext.replace("docs/", "")
                            if link.text.endswith("[1]"):
                                type = "Command"
                            elif link.text.endswith("[5]"):
                                type = "File"
                            elif (
                                link.text.endswith("[7]")
                                or link.text[0].isupper()
                            ):
                                type = "Guide"
                            else:
                                type = "Unknown"
                            sections.update({path: (name, type)})
                        link["href"] = path.replace("docs/", "")
                else:
                    link_parts = link["href"].split("#")
                    if index:
                        ext = ".html"
                    else:
                        ext = ""
                    if link_parts[0] != "":
                        link[
                            "href"
                        ] = f"{link_parts[0][1:]}{ext}#{link_parts[1]}"
    return soup


def misc_fixes():
    global sections
    pages = {
        "api-simple-ipc",
        "api-merge",
        "api-error-handling",
        "api-parse-options",
    }
    for page in pages:
        get_doc(
            page, type="Interface", ext=".html", fixlinks=False, update=True
        )
    url = "https://api.github.com/repos/git/git/contents/Documentation/howto"
    dir = eval(requests.get(url, stream=True).content.decode("utf-8"))
    url = "https://raw.githubusercontent.com/git/git/master/Documentation/howto"
    for entry in dir:
        get_doc(
            f"{entry['name']}",
            url,
            type="Guide",
            ext=".html",
            txt2html=True,
            update=True,
        )
    try:
        os.rmdir(os.path.join(output, "docs/howto"))
    except (OSError):
        pass
    deletions = [
        "docs/api-index.html",
        "docs/howto/update-hook-example.html",
        "docs/howto/setup-git-server-over-http.html",
        "docs/howto/revert-a-faulty-merge.html",
        "docs/howto-index.html",
    ]
    for path in deletions:
        try:
            sections.pop(path)
        except (KeyError):
            pass
    sections.update(
        {"docs/git.html#_environment_variables": ("Variables", "Environment")}
    )
    sections.update({"docs/partial-clone.html": ("partial-clone", "Interface")})
    sections.update({"docs/gitglossary.html": ("Git Glossary", "Glossary")})


def update_db(sections):
    for path, (name, type) in sections.items():
        cur.execute(
            "INSERT OR IGNORE INTO searchIndex(name,type,path) VALUES (?,?,?)",
            (name, type, path),
        )
        print("DB add >> name: %s, path: %s" % (name, path))


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
    with open(f"{docset_name}/Contents/Info.plist", "w") as f:
        f.write(info)


if __name__ == "__main__":
    initialise()
    get_git(f"{root_url}/git")
    get_index(root_url)
    add_docs(2, len(sections) - 1)
    misc_fixes()
    update_db(sections)
    add_info_plist()
    db.commit()
    db.close()
