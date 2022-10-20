"""
    Generate Dash docset for Git
    http://git-scm.com/docs
"""
import itertools
import json
import os
import re
import sqlite3
from shutil import copy
from sys import argv

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
    global lang
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
    if len(argv) > 1:
        lang = argv[1]
    else:
        lang = "en"


def get_git(url):
    global lang
    global sections
    # Unwisely, the Git manpages translation project
    # chose to translate tag id attributes.
    # Furthermore, current translations of 'git.html'
    # are lacking the 'Guides' section etc.
    # So, always fetch the English version to
    # trawl for links, then download and save
    # the preferred language version
    page = requests.get(url).text
    soup = bs(page, parser)
    title = soup.find("title")
    soup = soup.find(id="main")
    files = {"gitattributes", "gitignore", "gitmailmap", "gitmodules"}
    sects = {
        "_high_level_commands": "Command",
        "_low_level_commands": "Command",
        "_guides": "Guide",
        "_repository_command_and_file_interfaces": "Interface",
        "_file_formats_protocols_and_other_developer_interfaces": None,
    }
    pattern = str(list(sects.keys()))[3:-3].replace("', '", "|")
    headings = soup.findAll("h2", {"id": re.compile(pattern)})
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
    if lang != "en":
        page = requests.get(f"{url}/{lang}").text
        soup = bs(page, parser)
        soup = soup.find(id="main")
        fix_links(soup, updatesections=False)
    soup.insert(0, title)
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
            page_id = path.split("/")[-1].split(".")[0]
            get_doc(page_id, fixlinks=True)
    start = end + 1
    end = len(sections) - 1
    if end > start_prev:
        add_docs(start, end)


def get_doc(
    page_id,
    url="http://git-scm.com/docs",
    ignorelang=False,
    strip_ext=True,
    txt2html=False,
    fixlinks=False,
    updatesections=False,
    type="",
):
    global lang
    global sections
    print(f"Downloading document: {page_id}")
    if ignorelang or lang == "en":
        suffix = ""
    else:
        suffix = f"/{lang}"
    response = requests.get(f"{url}/{page_id}{suffix}", stream=True)
    if response.status_code != 200:
        print(f"HTTP error: {response.status_code}")
        return
    if strip_ext:
        page_id = page_id.split(".")[0]
    if txt2html:
        doc = (
            f"<html><body><pre><title>{page_id}"
            f"</title>{response.text}</pre></body></html>"
        )
    else:
        soup = bs(response.text, parser)
        title_tag = soup.new_tag("title")
        title_tag.append(page_id)
        soup = soup.find(id="main")
        soup.insert(0, title_tag)
        if fixlinks:
            soup = fix_links(soup)
        doc = str(soup)
    with open(
        os.path.join(output, f"docs/{page_id}.html"),
        "w",
        encoding="iso-8859-1",
        errors="ignore",
    ) as f:
        f.write(doc)
        print("Success")
    if updatesections:
        sections.update({f"docs/{page_id}.html": (page_id, type)})


def fix_links(soup, index=False, updatesections=True):
    global lang
    global sections
    for link in soup.findAll("a", {"href": True}):
        if link.attrs:
            pattern = re.compile("^(http|mailto)")
            if not re.match(pattern, link["href"]):
                if "#" not in link.attrs["href"]:
                    path_noext = re.split(f"(^/|/{lang})", link["href"])[2]
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
                            if updatesections:
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
    global lang
    global sections
    page_ids = {
        "api-simple-ipc",
        "api-merge",
        "api-error-handling",
        "api-parse-options",
    }
    for page_id in page_ids:
        get_doc(
            page_id,
            fixlinks=False,
            updatesections=True,
            type="Interface",
        )
    url = "https://api.github.com/repos/git/git/contents/Documentation/howto"
    dir = json.loads(requests.get(url).content.decode())
    url = "https://raw.githubusercontent.com/git/git/master/Documentation/howto"
    for entry in dir:
        get_doc(
            entry["name"],
            url,
            ignorelang=True,
            txt2html=True,
            updatesections=True,
            type="Guide",
        )
    get_doc(
        "gitweb.conf",
        ignorelang=True,
        strip_ext=False,
        fixlinks=True,
        type="File",
    )
    get_doc(
        "gitweb",
        fixlinks=True,
        type="Interface",
    )
    sections.update({"docs/gitweb.html": ("gitweb", "Interface")})
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
        # pt_BR clanger
        "docs/gitignorar.html",
    ]
    for path in deletions:
        try:
            sections.pop(path)
        except (KeyError):
            pass
    if lang == "en":
        jump_variables = "_environment_variables"
    else:
        if lang == "de":
            jump_commands = "_git_befehle"
            jump_variables = "_umgebungsvariablen"
        elif lang == "pt_BR":
            jump_commands = "_os_comandos_do_git"
            jump_variables = "_as_vari%C3%A1veis_do_ambiente"
        with open(
            os.path.join(output, "index.html"),
            "r+",
            encoding="iso-8859-1",
            errors="ignore",
        ) as f:
            html = f.read().replace("_git_commands", jump_commands)
            f.seek(0)
            f.write(html)
            f.truncate()
    sections.update(
        {f"docs/git.html#{jump_variables}": ("Variables", "Environment")}
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
