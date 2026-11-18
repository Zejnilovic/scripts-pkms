// Reveals the home page's sections as they scroll into view. Without this script, or with reduced motion, everything
// is simply shown: the CSS hides elements only under html.js.
(function () {
  var root = document.documentElement;
  if (!("IntersectionObserver" in window)) return;
  root.classList.add("js");
  function start() {
    var items = document.querySelectorAll(".db-reveal");
    if (!items.length) return;
    var seen = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          seen.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.15 });
    items.forEach(function (item) { seen.observe(item); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
