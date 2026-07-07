/* ============================================================
   cosmos.js — 星野（背景）とアイオーンの環を注入する共通スクリプト
   prefers-reduced-motion を尊重します。
   ============================================================ */
(function () {
  "use strict";

  /* --- アイオーンの環（ページ上部中央の同心円） --- */
  var rings = document.createElement("div");
  rings.id = "cosmos-rings";
  rings.setAttribute("aria-hidden", "true");
  rings.innerHTML =
    '<svg width="720" height="720" viewBox="0 0 720 720">' +
    '<circle class="ring-a" cx="360" cy="360" r="170" stroke-width="0.6" opacity="0.5" stroke-dasharray="4 10"/>' +
    '<circle class="ring-b" cx="360" cy="360" r="245" stroke-width="0.5" opacity="0.3" stroke-dasharray="1 14"/>' +
    '<circle cx="360" cy="360" r="320" stroke-width="0.4" opacity="0.16"/>' +
    '<circle class="ring-a" cx="360" cy="360" r="140" stroke-width="0.4" opacity="0.24"/>' +
    "</svg>";

  /* --- 星野キャンバス --- */
  var canvas = document.createElement("canvas");
  canvas.id = "cosmos-starfield";
  canvas.setAttribute("aria-hidden", "true");

  function mount() {
    document.body.insertBefore(rings, document.body.firstChild);
    document.body.insertBefore(canvas, document.body.firstChild);
    start();
  }

  function start() {
    var ctx = canvas.getContext("2d");
    var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var stars = [];

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      var n = Math.floor((canvas.width * canvas.height) / 7000);
      stars = [];
      for (var i = 0; i < n; i++) {
        stars.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          r: Math.random() * 1.1 + 0.2,
          p: Math.random() * Math.PI * 2,   // 明滅の位相
          s: 0.4 + Math.random() * 0.8,     // 明滅速度
          gold: Math.random() < 0.08        // 一部だけ金色
        });
      }
    }

    function draw(t) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var i = 0; i < stars.length; i++) {
        var st = stars[i];
        var a = reduced ? 0.5 : 0.32 + 0.34 * Math.sin(st.p + t * 0.001 * st.s);
        ctx.globalAlpha = Math.max(0.06, a);
        ctx.fillStyle = st.gold ? "#d4af6a" : "#cfd2ec";
        ctx.beginPath();
        ctx.arc(st.x, st.y, st.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      if (!reduced) requestAnimationFrame(draw);
    }

    window.addEventListener("resize", function () {
      resize();
      if (reduced) draw(0);
    });
    resize();
    if (reduced) draw(0);
    else requestAnimationFrame(draw);
  }

  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
