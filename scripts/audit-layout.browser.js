/*
 * Layout + reveal audit. Paste into the console on preview.html.
 *
 *   py -m http.server 4599 --directory .
 *   open http://localhost:4599/preview.html
 *
 * Why this exists as a browser script rather than part of verify.py: two of the
 * things that can go wrong here are invisible to a static checker.
 *
 * 1. Whether the portrait and card actually sit on one row. That depends on the
 *    width of the collapsed newline between the two <img> tags, which is a font
 *    metric, not a number you choose. An earlier revision was 0.4px too wide
 *    and the card silently wrapped onto its own line — both images still
 *    rendered perfectly, the layout was just wrong.
 *
 * 2. Whether the reveal animations end in a visible state. If they do not, the
 *    panels render blank.
 *
 * Note on running this in a headless or hidden pane: CSS animations do not
 * advance while a document is not compositing (document.visibilityState ===
 * "hidden"), so every element stays frozen at its from-state. This script
 * therefore forces each animation to finish via the Web Animations API rather
 * than waiting on wall-clock time, which makes the result deterministic
 * wherever it runs.
 */
(async () => {
  const bb = el => el.getBoundingClientRect();
  const files = ["ascii-portrait.svg", "info-card.svg",
                 "contrib-heatmap.svg", "shipped.svg"];
  const report = { env: { reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
                          visibility: document.visibilityState } };

  // --- side-by-side row -----------------------------------------------------
  const p = document.getElementById("pA"), c = document.getElementById("cA");
  if (p && c) {
    const P = bb(p), C = bb(c);
    report.row = {
      sameRow: Math.abs(P.top - C.top) < 2,
      gutter: +(C.left - P.right).toFixed(2),
      width: +(C.right - P.left).toFixed(1),
      container: Math.round(bb(p.parentElement).width),
      heightDelta: +Math.abs(P.height - C.height).toFixed(1),
    };
    report.row.slack = +(report.row.container - report.row.width).toFixed(1);
    report.row.PASS = report.row.sameRow && report.row.slack >= 0
                      && report.row.heightDelta <= 12;
  }

  // --- phone ----------------------------------------------------------------
  const ph = document.getElementById("ph");
  if (ph) {
    report.phone = { scrollW: ph.scrollWidth, clientW: ph.clientWidth,
                     PASS: ph.scrollWidth <= ph.clientWidth };
  }
  report.docOverflow = document.documentElement.scrollWidth > window.innerWidth;

  // --- reveal end state -----------------------------------------------------
  const host = document.createElement("div");
  host.style.cssText = "position:absolute;left:0;top:0;width:900px;opacity:.01";
  document.body.appendChild(host);

  report.reveal = {};
  for (const f of files) {
    const box = document.createElement("div");
    // innerHTML is required, not incidental: the point of the probe is to let
    // the browser's own CSS engine parse the SVG's <style> block and resolve
    // the animations. Sanitising would strip exactly what is being tested.
    // The input is a file this repo generated, fetched from the local static
    // server serving this same directory — there is no external content path.
    box.innerHTML = await (await fetch("/" + f)).text();
    host.appendChild(box);
    await new Promise(r => setTimeout(r, 50));

    const els = [...box.querySelectorAll(".wipe,.fade,.pop")];
    els.flatMap(e => e.getAnimations()).forEach(a => { try { a.finish(); } catch {} });
    await new Promise(r => setTimeout(r, 20));

    // A revealed element is opaque and unclipped. Chrome reports the finished
    // clip-path as "inset(0px 0% 0px 0px)" — it keeps the % unit it animated
    // from — so match on "every side is zero" rather than on one exact string.
    let visible = 0;
    for (const el of els) {
      const cs = getComputedStyle(el);
      const clipOK = cs.clipPath === "none" ||
                     /^inset\((0px|0%)(\s+(0px|0%)){0,3}\)$/.test(cs.clipPath);
      if (parseFloat(cs.opacity) > 0.9 && clipOK) visible++;
    }
    report.reveal[f] = { animated: els.length, revealed: visible,
                         PASS: els.length > 0 && visible === els.length };
    box.remove();
  }
  host.remove();

  const fails = JSON.stringify(report).match(/"PASS":false/g);
  report.RESULT = fails ? `${fails.length} FAILED` : "all passed";
  console.log(JSON.stringify(report, null, 2));
  return report;
})();
