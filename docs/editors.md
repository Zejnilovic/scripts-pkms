# Using a vault from an editor

A vault is plain Markdown, so any editor opens it. pkm does the rules: an editor only runs a command and uses what it prints. Every command prints paths relative to the vault, and lines as `path:line: text`, so the editor can open the file at that line. The [README](../README.md) has the commands; [contract.md](contract.md) has the exact output.

Three things help any editor:

- **Run pkm in the vault.** Any folder inside the vault works. From an editor, pass `--vault <folder>` (or set `PKM_VAULT`) so the command does not depend on the current folder.
- **Follow links.** `pkm path <name>` prints the file a `[[link]]` points to.
- **Read results.** `pkm find --json <words>` prints JSON Lines with `path`, `line` and `text`, for a picker.

## Neovim

A Neovim plugin for pkm is planned in this repo. Until it exists, this recipe in your config (`init.lua`) adds commands to open today's page, add entries and tasks, fill the quickfix list from `find`, `tasks` and `check`, and follow `[[links]]` with `gf`. Set `vault` to your vault's folder.

```lua
local vault = vim.fn.expand("~/vault")

-- Runs pkm in the vault and returns its output lines. Exit 1 means nothing matched or a check found problems, so
-- only exit 2 (a wrong call) is an error here.
local function pkm(args)
  local out = vim.fn.systemlist(vim.list_extend({ "pkm", "--vault", vault }, args))
  if vim.v.shell_error == 2 then
    vim.notify(table.concat(out, "\n"), vim.log.levels.ERROR)
    return nil
  end
  return out
end

-- Opens the path pkm prints, relative to the vault.
local function open(args)
  local out = pkm(args)
  if out and out[1] then vim.cmd.edit(vim.fn.fnameescape(vault .. "/" .. out[1])) end
end

-- Fills the quickfix list from path:line: text lines, as find, tasks and check print them.
local function quickfix(args, title)
  local items = {}
  for _, line in ipairs(pkm(args) or {}) do
    local file, lnum, text = line:match("^%-? ?(.-):(%d+): (.*)$")
    if file then table.insert(items, { filename = vault .. "/" .. file, lnum = tonumber(lnum), text = text }) end
  end
  vim.fn.setqflist({}, " ", { title = title, items = items })
  if #items > 0 then vim.cmd("copen") else vim.notify("No matches", vim.log.levels.INFO) end
end

local function say(args)
  local out = pkm(args)
  if out then vim.notify(table.concat(out, "\n")) end
end

vim.api.nvim_create_user_command("PkmDay", function() open({ "day" }) end, {})
vim.api.nvim_create_user_command("PkmAdd", function(o) say(vim.list_extend({ "add" }, o.fargs)) end, { nargs = "+" })
vim.api.nvim_create_user_command("PkmTodo", function(o) say(vim.list_extend({ "todo" }, o.fargs)) end, { nargs = "+" })
vim.api.nvim_create_user_command("PkmDone", function(o) say(vim.list_extend({ "done" }, o.fargs)) end, { nargs = "+" })
vim.api.nvim_create_user_command("PkmNew", function(o)
  open({ "new", o.fargs[1], table.concat(vim.list_slice(o.fargs, 2), " ") })
end, { nargs = "+" })
vim.api.nvim_create_user_command("PkmFind", function(o) quickfix(vim.list_extend({ "find" }, o.fargs), "pkm find") end, { nargs = "+" })
vim.api.nvim_create_user_command("PkmTasks", function() quickfix({ "tasks" }, "pkm tasks") end, {})
vim.api.nvim_create_user_command("PkmCheck", function() quickfix({ "check" }, "pkm check") end, {})

-- gf on a [[link]] opens the note it names, wherever it is in the vault.
vim.api.nvim_create_autocmd("BufEnter", {
  pattern = vault .. "/*.md",
  callback = function(event)
    vim.keymap.set("n", "gf", function()
      local line, col = vim.api.nvim_get_current_line(), vim.fn.col(".")
      for s, inner, e in line:gmatch("()%[%[(.-)%]%]()") do
        if col >= s and col < e then
          local name = inner:match("^[^|#]+")
          return open({ "path", name })
        end
      end
      vim.cmd("normal! gf")
    end, { buffer = event.buf })
  end,
})
```

Usage: `:PkmDay`, `:PkmAdd John says the budget needs sign-off`, `:PkmTodo Send the offer --due friday --high`, `:PkmTodo Pay the rent --every 1m`, `:PkmDone invoice`, `:PkmNew person Jane Doe`, `:PkmFind mobile app` (every word), `:PkmTasks` and `:PkmCheck`. Arguments are split on spaces, so do not quote them. Use `:cnext` and `:copen` to move through the quickfix list.

For completion of `[[links]]`, backlinks and renames across the vault, use a Markdown language server that reads wiki links, such as markdown-oxide, or obsidian.nvim. Both read the vault as it is.

## VS Code

Open the vault folder as the workspace. The repo ships a task file, [`share/pkm/editors/vscode/tasks.json`](../share/pkm/editors/vscode/tasks.json). Copy it to `.vscode/tasks.json` in the vault:

```bash
mkdir -p .vscode && cp <pkm folder>/share/pkm/editors/vscode/tasks.json .vscode/tasks.json
```

`<pkm folder>` is the clone of this repo, or the folder `make install` or `install.sh` put pkm in (its `share/` folder). Then run **Tasks: Run Task** and pick:

- **pkm: day** prints today's page path. To open it, run `code "$(pkm day)"` in the terminal.
- **pkm: add** asks for an entry and adds it to today's Log.
- **pkm: find** asks for words and passes each one as its own argument, so `app mobile` finds lines with both words, in any order.
- **pkm: tasks** and **pkm: check** list their `path:line: text` lines in the Problems panel, where you can click each one.

For `[[links]]`, completion and backlinks, the Foam extension reads the same wiki links.

## Obsidian

Obsidian needs nothing from pkm: it opens the vault folder and reads the links, frontmatter and tasks. pkm reads the same files. Two settings make the two agree:

- **Files and links**: keep "Use [[Wikilinks]]" on, and set "New link format" to "Shortest path when possible", so links stay names.
- **Daily notes** (core plugin): folder `daybook`, date format `YYYY/MM/YYYY-MM-DD`, so Obsidian finds the day's page where `pkm day` makes it. For the template, run `pkm templates eject day` once; it copies pkm's day page (`# {{title}}`, `## Tasks`, `## Log`) to `templates/day.md`, and then set the template to `templates/day`. In a shared vault the pages end with the writer's name, so set the daily notes to that writer's pages.
- **Templates** (core plugin): set the template folder to `templates`. Obsidian fills `{{title}}`, `{{date}}` and `{{time}}`, which pkm's templates also use.
- **Excluded files**: add `archive/` and `templates/` if they should stay out of search and the graph.

Obsidian skips folders whose names start with a dot, so `.pkm/` stays out of its way.

To run pkm from Obsidian, use a terminal in the vault folder, or the community "Shell commands" plugin, which is not required.

## On a phone

Any app that writes Markdown into the vault can capture: an entry is `- HH:MM text` at the end of the day's Log. From a shell, `pkm add "text"` or `pkm add -` (text on stdin) does that for you and prints `path:line`.

## Planned

A Neovim plugin for pkm is planned in this repo. It will call the same commands as the recipe above.
