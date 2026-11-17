# Homebrew formula for pkm, for the owner's tap. scripts/formula.sh fills the url and the sha256 from the tarball that
# make dist built. Until then the sha256 is a placeholder, and brew refuses to install the formula.
class Pkm < Formula
  desc "Command line for plain Markdown vaults: day pages, tasks, links and the close"
  homepage "https://github.com/Zejnilovic/scripts-pkms"
  url "https://github.com/Zejnilovic/scripts-pkms/releases/download/v0.1.0/pkm-0.1.0.tar.gz"
  sha256 "PLACEHOLDER_FILLED_BY_SCRIPTS_FORMULA_SH"
  license "MIT"

  depends_on "ripgrep"
  depends_on "jq"

  def install
    libexec.install "bin", "lib", "share", "VERSION"
    bin.install_symlink libexec/"bin/pkm"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pkm version")
  end
end
