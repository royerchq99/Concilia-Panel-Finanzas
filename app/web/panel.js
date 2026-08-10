/* Panel de conciliación de pautas · sin librerías, todo local */
"use strict";

var usandoEjemplo = false;

/* ------------------------------------------------------------ utilidades */
function $(s) { return document.querySelector(s); }
function $$(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }

function dinero(v) {
  if (v === null || v === undefined) return "SIN DATOS";
  return Math.round(v).toLocaleString("es-ES");
}

function escapar(t) {
  var d = document.createElement("div");
  d.textContent = t === null || t === undefined ? "" : String(t);
  return d.innerHTML;
}

/* Convierte el markdown mínimo que usa el chat: **negrita** y listas con '- '. */
function formato(texto) {
  var lineas = String(texto).split("\n");
  var html = "", enLista = false;
  lineas.forEach(function (l) {
    var esItem = /^\s*-\s+/.test(l);
    if (esItem && !enLista) { html += "<ul>"; enLista = true; }
    if (!esItem && enLista) { html += "</ul>"; enLista = false; }
    var t = escapar(esItem ? l.replace(/^\s*-\s+/, "") : l);
    t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html += esItem ? "<li>" + t + "</li>" : (t ? "<p>" + t + "</p>" : "");
  });
  if (enLista) html += "</ul>";
  return html;
}

function esperar(texto) {
  $("#texto-espera").textContent = texto || "Trabajando…";
  $("#espera").hidden = false;
}
function finEspera() { $("#espera").hidden = true; }

function avisar(mensaje, clase) {
  var a = $("#aviso-cerrar");
  a.className = "aviso " + (clase || "");
  a.innerHTML = formato(mensaje);
  a.hidden = false;
}
function limpiarAviso() { $("#aviso-cerrar").hidden = true; }

function pedir(url, opciones) {
  return fetch(url, opciones).then(function (r) {
    return r.json().catch(function () { return {}; }).then(function (j) {
      if (!r.ok) throw new Error(j.error || ("Error " + r.status));
      return j;
    });
  });
}

/* ------------------------------------------------------------ pestañas */
function irA(nombre) {
  $$(".pestana").forEach(function (b) {
    b.classList.toggle("activa", b.dataset.panel === nombre);
  });
  $$(".panel").forEach(function (p) {
    p.classList.toggle("activa", p.id === "panel-" + nombre);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

$$(".pestana").forEach(function (b) {
  b.addEventListener("click", function () {
    if (!b.disabled) irA(b.dataset.panel);
  });
});

function habilitar(nombres) {
  $$(".pestana").forEach(function (b) {
    if (nombres.indexOf(b.dataset.panel) >= 0) b.disabled = false;
  });
}

/* ------------------------------------------------------------ archivos */
function pintarLista(id, archivos, tipo) {
  var ul = $(id);
  ul.innerHTML = "";
  if (!archivos.length) {
    var li = document.createElement("li");
    li.className = "vacia";
    li.textContent = "Todavía no hay " + tipo;
    ul.appendChild(li);
    return;
  }
  archivos.forEach(function (a) {
    var li = document.createElement("li");
    li.innerHTML = "<span>" + escapar(a.nombre) + "</span><span>" + a.kb + " KB</span>";
    ul.appendChild(li);
  });
}

function refrescarEstado() {
  return pedir("/api/estado").then(function (e) {
    $("#firma").textContent = e.marca || "";
    if (!$("#mes").options.length) {
      e.meses.forEach(function (m, i) {
        var o = document.createElement("option");
        o.value = m; o.textContent = m;
        $("#mes").appendChild(o);
      });
      var hoy = new Date();
      $("#mes").value = e.meses[hoy.getMonth() === 0 ? 11 : hoy.getMonth() - 1];
      $("#anio").value = e.anio_sugerido;
    }
    pintarLista("#lista-pautas", e.pautas, "ningún Excel de pauta");
    pintarLista("#lista-facturas", e.facturas, "ninguna factura");
    return e;
  });
}

function subir(tipo, ficheros) {
  if (!ficheros || !ficheros.length) return;
  var fd = new FormData();
  fd.append("tipo", tipo);
  for (var i = 0; i < ficheros.length; i++) fd.append("archivos", ficheros[i]);
  esperar("Subiendo " + ficheros.length + " archivo(s)…");
  pedir("/api/subir", { method: "POST", body: fd })
    .then(function (r) {
      usandoEjemplo = false;
      pintarLista("#lista-pautas", r.pautas, "ningún Excel de pauta");
      pintarLista("#lista-facturas", r.facturas, "ninguna factura");
      if (r.rechazados.length) {
        avisar("No he podido aceptar " + r.rechazados.length + " archivo(s):\n" +
          r.rechazados.map(function (x) { return "- **" + x.nombre + "** — " + x.motivo; }).join("\n"));
      } else {
        limpiarAviso();
      }
    })
    .catch(function (e) { avisar(e.message); })
    .then(finEspera);
}

["pautas", "facturas"].forEach(function (tipo) {
  var zona = $("#zona-" + tipo);
  var input = zona.querySelector("input[type=file]");
  input.addEventListener("change", function () {
    marcarModoEjemplo(false);
    subir(tipo, input.files);
    input.value = "";
  });
  ["dragenter", "dragover"].forEach(function (ev) {
    zona.addEventListener(ev, function (e) {
      e.preventDefault(); zona.classList.add("encima");
    });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    zona.addEventListener(ev, function (e) {
      e.preventDefault(); zona.classList.remove("encima");
    });
  });
  zona.addEventListener("drop", function (e) {
    marcarModoEjemplo(false);
    subir(tipo, e.dataTransfer.files);
  });
});

$("#btn-vaciar").addEventListener("click", function () {
  esperar("Vaciando…");
  pedir("/api/vaciar", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  }).then(function (r) {
    usandoEjemplo = false;
    marcarModoEjemplo(false);
    pintarLista("#lista-pautas", r.pautas, "ningún Excel de pauta");
    pintarLista("#lista-facturas", r.facturas, "ninguna factura");
    avisar("Listo, he borrado " + r.borrados + " archivo(s).", "ok");
  }).catch(function (e) { avisar(e.message); }).then(finEspera);
});

$("#btn-ejemplo").addEventListener("click", function () {
  esperar("Creando el ejemplo de práctica…");
  pedir("/api/ejemplo", { method: "POST" })
    .then(function (r) {
      usandoEjemplo = true;
      $("#mes").value = "Julio";
      $("#anio").value = 2026;
      // Se pintan los archivos DEL EJEMPLO: si no, las listas siguen mostrando
      // entrada/ (vacía) y parece que no ha pasado nada.
      pintarLista("#lista-pautas", r.pautas, "ningún Excel de pauta");
      pintarLista("#lista-facturas", r.facturas, "ninguna factura");
      marcarModoEjemplo(true);
      avisar("Ejemplo listo: dos clientes inventados con **16 errores metidos a " +
        "propósito**. Está puesto en Julio de 2026. Pulsa **Conciliar** y mira si " +
        "los encuentra todos.", "info");
    })
    .catch(function (e) { avisar(e.message); })
    .then(finEspera);
});

/* Deja claro en pantalla que lo que se va a conciliar es el ejemplo, no tus datos. */
function marcarModoEjemplo(activo) {
  $$(".caja-subida").forEach(function (z) {
    z.classList.toggle("modo-ejemplo", activo);
  });
  var etiqueta = $("#etiqueta-ejemplo");
  if (activo && !etiqueta) {
    etiqueta = document.createElement("div");
    etiqueta.id = "etiqueta-ejemplo";
    etiqueta.className = "etiqueta-ejemplo";
    etiqueta.innerHTML = "Estás usando el <strong>ejemplo de práctica</strong> " +
      "(datos inventados). <button class='enlace' id='btn-salir-ejemplo' " +
      "type='button'>Volver a mis archivos</button>";
    $(".rejilla-subida").insertAdjacentElement("beforebegin", etiqueta);
    $("#btn-salir-ejemplo").addEventListener("click", function () {
      usandoEjemplo = false;
      marcarModoEjemplo(false);
      limpiarAviso();
      refrescarEstado();
    });
  } else if (!activo && etiqueta) {
    etiqueta.remove();
  }
}

/* ------------------------------------------------------------ conciliar */
function bandaDe(pct, comparables) {
  if (!comparables) return ["critica", "No se pudo conciliar nada",
    "Ninguna campaña tiene pauta y factura a la vez. Falta algún archivo."];
  if (pct >= 90) return ["buena", "La facturación cuadra",
    "Casi todo lo que se ejecutó se cobró por el mismo importe."];
  if (pct >= 70) return ["aceptable", "La facturación cuadra con excepciones",
    "Hay campañas donde lo cobrado no coincide con lo ejecutado."];
  if (pct >= 40) return ["floja", "Hay bastante que revisar",
    "Más de una de cada tres campañas conciliables tiene diferencias."];
  return ["critica", "La facturación no cuadra",
    "La mayor parte de lo facturado no coincide con lo ejecutado."];
}

function tarjetas(destino, pares) {
  var d = $(destino);
  d.innerHTML = "";
  pares.forEach(function (p) {
    var el = document.createElement("div");
    el.className = "dato";
    el.innerHTML = "<div class='k'>" + escapar(p[0]) + "</div>" +
      "<div class='v'>" + escapar(p[1]) + "</div>";
    d.appendChild(el);
  });
}

function pintarResultado(r) {
  var pct = r.comparables ? Math.round(r.cuadran / r.comparables * 100) : 0;
  var b = bandaDe(pct, r.comparables);
  $("#veredicto").className = "veredicto " + b[0];
  $("#veredicto").innerHTML =
    "<div class='cifra'>" + pct + " %</div>" +
    "<div class='etiqueta'>" + escapar(b[1]) + "</div>" +
    "<div class='detalle'>" + escapar(b[2]) + " " + r.cuadran + " de " +
    r.comparables + " campañas conciliables cuadran. Las " +
    (r.campanas - r.comparables) + " que no tienen factura o no tienen pauta no " +
    "cuentan en este porcentaje.</div>";

  tarjetas("#cifras", [
    ["Campañas", r.campanas],
    ["Clientes", r.clientes],
    ["Presupuesto", dinero(r.presupuesto)],
    ["Consumido", dinero(r.consumido)],
    ["Facturado", dinero(r.facturado)]
  ]);
  tarjetas("#estados-fact", Object.keys(r.facturacion).map(function (k) {
    return [k, r.facturacion[k]];
  }));
  tarjetas("#estados-ejec", Object.keys(r.ejecucion).map(function (k) {
    return [k, r.ejecucion[k]];
  }));

  var inc = $("#bloque-incidencias");
  if (!r.incidencias.length) {
    inc.innerHTML = "";
  } else {
    var f = r.incidencias.map(function (i) {
      return "<tr><td>" + escapar(i.archivo) + "</td><td>" + escapar(i.tipo) +
        "</td><td>" + escapar(i.detalle) + "</td></tr>";
    }).join("");
    inc.innerHTML = "<h2>Incidencias (" + r.incidencias.length + ")</h2>" +
      "<div class='tabla-scroll'><table><tr><th>Archivo</th><th>Tipo</th>" +
      "<th>Qué pasa</th></tr>" + f + "</table></div>";
  }

  $("#marco-informe").src = "/api/informe?t=" + Date.now();
  habilitar(["resultado", "informe", "chat"]);
  reiniciarChat();
}

$("#btn-conciliar").addEventListener("click", function () {
  limpiarAviso();
  var cuerpo = {
    mes: $("#mes").value,
    anio: $("#anio").value,
    ejemplo: usandoEjemplo
  };
  if ($("#trm").value) cuerpo.trm = $("#trm").value;

  esperar("Leyendo archivos y cruzando campañas…");
  pedir("/api/conciliar", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo)
  }).then(function (r) {
    pintarResultado(r);
    if (r.aviso_trm) {
      $("#campo-trm").hidden = false;
      avisar(r.aviso_trm, "info");
    }
    irA("resultado");
  }).catch(function (e) {
    avisar(e.message);
  }).then(finEspera);
});

$("#btn-ver-informe").addEventListener("click", function () { irA("informe"); });

/* ------------------------------------------------------------ chat */
var SUGERENCIAS = ["¿Cómo fue el mes?", "¿Qué no cuadra?",
  "¿Cuál es la mayor desviación?", "¿Qué campañas no tienen factura?",
  "¿Qué se facturó sin pauta?", "Campañas de Google", "¿Qué clientes hay?"];

function mensaje(texto, quien, tabla) {
  var d = document.createElement("div");
  d.className = "msj " + quien;
  if (quien === "yo") {
    d.textContent = texto;
  } else {
    d.innerHTML = formato(texto);
    if (tabla && tabla.filas && tabla.filas.length) {
      var th = tabla.cabeceras.map(function (c) { return "<th>" + escapar(c) + "</th>"; }).join("");
      var tr = tabla.filas.map(function (f) {
        return "<tr>" + f.map(function (c, i) {
          var num = /^[\d.,]+$/.test(c) || c === "SIN DATOS";
          var mono = i === 0;
          return "<td class='" + (num ? "num" : "") + (mono ? " mono" : "") + "'>" +
            escapar(c) + "</td>";
        }).join("") + "</tr>";
      }).join("");
      var caja = document.createElement("div");
      caja.className = "tabla-scroll";
      caja.innerHTML = "<table><tr>" + th + "</tr>" + tr + "</table>";
      d.appendChild(caja);
    }
  }
  $("#chat-mensajes").appendChild(d);
  $("#chat-mensajes").scrollTop = $("#chat-mensajes").scrollHeight;
}

function preguntar(texto) {
  if (!texto.trim()) return;
  mensaje(texto, "yo");
  $("#chat-texto").value = "";
  pedir("/api/chat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pregunta: texto })
  }).then(function (r) {
    mensaje(r.texto, "panel", r.tabla);
  }).catch(function (e) {
    mensaje("No he podido responder: " + e.message, "panel");
  });
}

$("#chat-form").addEventListener("submit", function (e) {
  e.preventDefault();
  preguntar($("#chat-texto").value);
});

function reiniciarChat() {
  $("#chat-mensajes").innerHTML = "";
  mensaje("El cierre está calculado. Pregúntame lo que quieras sobre él: " +
    "respondo leyendo el consolidado, así que las cifras son las mismas que " +
    "las del informe.", "panel");
  var s = $("#chat-sugerencias");
  s.innerHTML = "";
  SUGERENCIAS.forEach(function (t) {
    var b = document.createElement("button");
    b.className = "chip"; b.type = "button"; b.textContent = t;
    b.addEventListener("click", function () { preguntar(t); });
    s.appendChild(b);
  });
}

/* ------------------------------------------------------------ arranque */
refrescarEstado().then(function (e) {
  if (e.hay_cierre) habilitar(["resultado", "informe", "chat"]);
}).catch(function () {
  avisar("No he podido hablar con el servidor. ¿Sigue abierta la ventana negra?");
});
