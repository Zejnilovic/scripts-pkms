"""MkDocs hooks for the documentation site. The docs stay plain Markdown that reads well on GitHub; these hooks only
adapt them for the site. The same file serves scripts-pkms and agentic-pkms; mkdocs.yml configures it under
extra.site_hooks:

  repo_blob: the GitHub address of this repo's files; links that leave docs/ (../README.md) point there.
  siblings:  {GitHub address of another repo's docs/: its site}. A link to a .md file there goes to its page.
  vaults:    {folder under docs/examples/: [title, description]}. Each example vault becomes browsable: [[name]] links
             go to the note, a note's frontmatter shows as a card (MkDocs would hide it), and the vault gets an index.
"""

import posixpath
import re

from mkdocs.structure.files import File

FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.M | re.S)
INLINE_CODE = re.compile(r"`[^`\n]+`")
LINK = re.compile(r"(\]\()([^)\s]+)(\))")
WIKILINK = re.compile(r"\[\[([^\]|#]+)(#[^\]|]*)?(?:\|([^\]]+))?\]\]")

names = {}  # vault -> {note name: src_uri}


def settings(config):
    return config["extra"].get("site_hooks", {})


def vault_of(src_uri, vaults):
    parts = src_uri.split("/")
    if len(parts) > 2 and parts[0] == "examples" and parts[1] in vaults:
        return parts[1]
    return None


def on_files(files, config):
    vaults = settings(config).get("vaults", {})
    names.clear()
    for f in files.documentation_pages():
        vault = vault_of(f.src_uri, vaults)
        if vault:
            names.setdefault(vault, {})[posixpath.splitext(posixpath.basename(f.src_uri))[0]] = f.src_uri
    for vault, (title, about) in vaults.items():
        pages = sorted(names.get(vault, {}).items(), key=lambda item: item[1])
        rel = lambda uri: posixpath.relpath(uri, f"examples/{vault}")
        lines = [f"# {title}", "", about, "", "These are the vault's files as they are. Links between them work, "
                 "and each note's frontmatter is shown at its top.", "", "## Day pages", ""]
        lines += [f"- [{n}]({rel(uri)})" for n, uri in pages if "/daybook/" in uri]
        lines += ["", "## Notes", ""]
        lines += [f'- [{n}]({rel(uri)}) <span class="db-path">{posixpath.dirname(rel(uri))}/</span>'
                  for n, uri in pages if "/daybook/" not in uri]
        files.append(File.generated(config, f"examples/{vault}/index.md", content="\n".join(lines) + "\n"))
    return files


def outside_code(markdown, change):
    """Apply change() to the text outside fenced and inline code."""
    out, last = [], 0
    for fence in FENCE.finditer(markdown):
        out.append(_inline(markdown[last:fence.start()], change))
        out.append(fence.group(0))
        last = fence.end()
    out.append(_inline(markdown[last:], change))
    return "".join(out)


def _inline(text, change):
    out, last = [], 0
    for code in INLINE_CODE.finditer(text):
        out.append(change(text[last:code.start()]))
        out.append(code.group(0))
        last = code.end()
    out.append(change(text[last:]))
    return "".join(out)


def page_url(path):
    """docs/ path of a .md file -> its page on the site: method.md -> method/, examples/README.md -> examples/."""
    stem = path[:-3]
    if stem in ("README", "index"):
        return ""
    if stem.endswith(("/README", "/index")):
        return stem.rsplit("/", 1)[0] + "/"
    return stem + "/"


def on_page_markdown(markdown, page, config, files):
    conf = settings(config)
    repo_blob = conf.get("repo_blob", "")
    siblings = conf.get("siblings", {})
    vault = vault_of(page.file.src_uri, conf.get("vaults", {}))
    here = posixpath.dirname(page.file.src_uri)

    def fix_link(match):
        before, target, after = match.groups()
        path, _, anchor = target.partition("#")
        anchor = f"#{anchor}" if anchor else ""
        for docs, site in siblings.items():
            if path.startswith(docs) and path.endswith(".md"):
                return before + site + page_url(path[len(docs):]) + anchor + after
        if re.match(r"^[a-z]+:|^#|^/", target):
            return match.group(0)
        resolved = posixpath.normpath(posixpath.join(here, path))
        if resolved == ".." or resolved.startswith("../"):
            return before + repo_blob + resolved[3:] + anchor + after
        if path.endswith("/"):  # a folder: GitHub lists it, the site has an index page for it
            return before + path + "index.md" + anchor + after
        return match.group(0)

    def fix_wikilinks(text):
        def repl(m):
            name, heading, alias = m.group(1).strip(), m.group(2) or "", m.group(3)
            label = alias or name
            target = names.get(vault, {}).get(name)
            if not target:
                return f'<span class="db-link db-link--missing" title="No note named {name} in this vault">[[{label}]]</span>'
            href = posixpath.relpath(target, here)
            anchor = "#" + re.sub(r"[^a-z0-9]+", "-", heading[1:].lower()).strip("-") if heading else ""
            return f'[<span class="db-bracket">[[</span>{label}<span class="db-bracket">]]</span>]({href}{anchor}){{ .db-link }}'
        return WIKILINK.sub(repl, text)

    def change(text):
        text = LINK.sub(fix_link, text)
        return fix_wikilinks(text) if vault else text

    markdown = outside_code(markdown, change)

    if vault and page.meta:
        props = "\n".join(f"{key}: {_yaml(value)}" for key, value in page.meta.items())
        card = f'<div class="db-props" markdown><span class="db-props__label">frontmatter</span>\n\n```yaml\n{props}\n```\n\n</div>\n\n'
        markdown = card + markdown
    return markdown


def _yaml(value):
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)
