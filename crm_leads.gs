// ═══════════════════════════════════════════════════════════════
//  PublicFlow — CRM Leads Sync · Google Apps Script
//  Kopiere diesen Code in: Erweiterungen → Apps Script
//  Dann: "Trigger hinzufügen" → syncLeads → Zeitgesteuert → täglich
// ═══════════════════════════════════════════════════════════════

// ── Konfiguration ──────────────────────────────────────────────
const CONFIG = {
  API_BASE:     "https://DEINE-RAILWAY-URL.railway.app",   // ← anpassen
  ADMIN_SECRET: "publicflow-admin-2026",                   // ← aus .env ADMIN_SECRET
  SHEET_NAME:   "CRM Leads",
  PIPELINE_SHEET: "Pipeline",
  STATS_SHEET:  "Stats",
};

// ── Spalten-Definition ─────────────────────────────────────────
const COLUMNS = [
  "📅 Registriert",
  "👤 Name",
  "📧 E-Mail",
  "🏢 Unternehmen",
  "🏭 Branche",
  "📍 Regionen",
  "💰 Plan",
  "✅ Abo-Status",
  "🔑 Keywords",
  "💶 Budget Min",
  "💶 Budget Max",
  "🎯 Matches",
  "📊 Lead-Score",
  "🏷️ Stage",
  "📝 Notizen",
  "🔗 Stripe ID",
];

// ── Farben & Styles ────────────────────────────────────────────
const COLORS = {
  header:     "#07070f",
  headerText: "#ffffff",
  blue:       "#2B6EFF",
  purple:     "#7C3AED",
  green:      "#10b981",
  orange:     "#f59e0b",
  red:        "#ef4444",
  grey:       "#6b7280",
  rowAlt:     "#f8f9ff",
  rowBase:    "#ffffff",
  pro:        "#EEF2FF",
  starter:    "#F0FDF4",
  none:       "#FFF7ED",
};

// ═══════════════════════════════════════════════════════════════
//  HAUPT-FUNKTION: Daten holen + Sheet befüllen
// ═══════════════════════════════════════════════════════════════
function syncLeads() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const data = fetchLeadsFromAPI();

  if (!data || !data.kunden) {
    SpreadsheetApp.getUi().alert("❌ API-Fehler: Keine Daten erhalten.");
    return;
  }

  setupLeadsTab(ss, data.kunden);
  setupStatsTab(ss, data.kunden);
  showToast(ss, `✅ ${data.kunden.length} Leads synchronisiert · Stand: ${new Date().toLocaleString("de-DE")}`);
}

// ── API-Aufruf ─────────────────────────────────────────────────
function fetchLeadsFromAPI() {
  const url = CONFIG.API_BASE + "/admin/export";
  const options = {
    method: "GET",
    headers: {
      "Authorization": "Bearer " + CONFIG.ADMIN_SECRET,
      "Content-Type":  "application/json",
    },
    muteHttpExceptions: true,
  };

  try {
    const response = UrlFetchApp.fetch(url, options);
    const code = response.getResponseCode();

    if (code === 200) {
      return JSON.parse(response.getContentText());
    } else if (code === 403) {
      throw new Error("Admin-Secret falsch (403). Bitte CONFIG.ADMIN_SECRET prüfen.");
    } else if (code === 429) {
      throw new Error("Rate-Limit erreicht (429). Bitte 60 Sekunden warten.");
    } else {
      throw new Error(`API-Fehler: HTTP ${code}`);
    }
  } catch (e) {
    Logger.log("❌ fetchLeadsFromAPI Fehler: " + e.message);
    SpreadsheetApp.getUi().alert("API-Fehler:\n" + e.message);
    return null;
  }
}

// ═══════════════════════════════════════════════════════════════
//  CRM LEADS TAB aufbauen
// ═══════════════════════════════════════════════════════════════
function setupLeadsTab(ss, kunden) {
  // Sheet holen oder neu erstellen
  let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_NAME, 0);
  } else {
    sheet.clearContents();
    sheet.clearFormats();
  }

  // ── Header-Zeile ──────────────────────────────────────────────
  const headerRange = sheet.getRange(1, 1, 1, COLUMNS.length);
  headerRange.setValues([COLUMNS]);
  headerRange.setBackground(COLORS.header);
  headerRange.setFontColor(COLORS.headerText);
  headerRange.setFontWeight("bold");
  headerRange.setFontSize(11);
  headerRange.setFontFamily("Google Sans, Arial, sans-serif");
  headerRange.setVerticalAlignment("middle");
  headerRange.setHorizontalAlignment("center");
  sheet.setFrozenRows(1);
  sheet.setRowHeight(1, 40);

  // ── Daten befüllen ─────────────────────────────────────────────
  const rows = kunden.map((k, idx) => {
    const score = calcLeadScore(k);
    const stage = getStage(k);
    return [
      k.registriert_am  || "",
      k.name            || "",
      k.email           || "",
      k.unternehmen     || "",
      k.branche         || "",
      k.regionen        || "",
      k.plan            || "kein Abo",
      k.abo_status      || "–",
      k.keywords        || "",
      k.min_budget      || 0,
      k.max_budget      || 0,
      k.matches_gesamt  || 0,
      score,
      stage,
      "",               // Notizen — manuell befüllen
      k.stripe_sub_id   || "",
    ];
  });

  if (rows.length > 0) {
    const dataRange = sheet.getRange(2, 1, rows.length, COLUMNS.length);
    dataRange.setValues(rows);
    dataRange.setFontSize(10);
    dataRange.setFontFamily("Google Sans, Arial, sans-serif");
    dataRange.setVerticalAlignment("middle");

    // Zeilen formatieren
    rows.forEach((row, i) => {
      const rowNum = i + 2;
      const plan = row[6];
      const rowRange = sheet.getRange(rowNum, 1, 1, COLUMNS.length);

      // Alternating row color
      if (plan === "pro" || plan === "Pro") {
        rowRange.setBackground(COLORS.pro);
      } else if (plan === "starter" || plan === "Starter") {
        rowRange.setBackground(COLORS.starter);
      } else {
        rowRange.setBackground(i % 2 === 0 ? COLORS.rowBase : COLORS.rowAlt);
      }

      sheet.setRowHeight(rowNum, 32);

      // Score-Zelle einfärben
      const scoreCell = sheet.getRange(rowNum, 13);
      const score = row[12];
      if (score >= 80) scoreCell.setBackground("#DCFCE7").setFontColor("#166534");
      else if (score >= 50) scoreCell.setBackground("#FEF9C3").setFontColor("#713F12");
      else scoreCell.setBackground("#FEE2E2").setFontColor("#991B1B");

      // Stage-Badge
      const stageCell = sheet.getRange(rowNum, 14);
      colorStage(stageCell, row[13]);

      // E-Mail klickbar
      const emailCell = sheet.getRange(rowNum, 3);
      if (row[2]) {
        emailCell.setFormula(`=HYPERLINK("mailto:${row[2]}","${row[2]}")`);
      }
    });
  }

  // ── Spaltenbreiten ─────────────────────────────────────────────
  const widths = [130, 160, 220, 180, 140, 160, 90, 100, 200, 100, 100, 80, 90, 110, 200, 150];
  widths.forEach((w, i) => sheet.setColumnWidth(i + 1, w));

  // ── Dropdown für "Stage" (Spalte 14) ──────────────────────────
  if (rows.length > 0) {
    const stageCol = sheet.getRange(2, 14, rows.length, 1);
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(["🆕 Neu", "📞 Kontaktiert", "🔥 Hot Lead", "✅ Kunde", "❌ Verloren"], true)
      .build();
    stageCol.setDataValidation(rule);
  }

  // ── Filter aktivieren ──────────────────────────────────────────
  sheet.getRange(1, 1, rows.length + 1, COLUMNS.length).createFilter();

  // ── Info-Zeile oben (Timestamp) ───────────────────────────────
  const lastRow = rows.length + 2;
  sheet.getRange(lastRow + 1, 1).setValue(`Zuletzt aktualisiert: ${new Date().toLocaleString("de-DE")}`);
  sheet.getRange(lastRow + 1, 1).setFontColor(COLORS.grey).setFontSize(9);

  Logger.log(`✅ CRM Leads Tab: ${rows.length} Zeilen geschrieben`);
}

// ═══════════════════════════════════════════════════════════════
//  STATS TAB aufbauen
// ═══════════════════════════════════════════════════════════════
function setupStatsTab(ss, kunden) {
  let sheet = ss.getSheetByName(CONFIG.STATS_SHEET);
  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.STATS_SHEET);
  } else {
    sheet.clearContents();
    sheet.clearFormats();
  }

  // Zahlen berechnen
  const total      = kunden.length;
  const proCount   = kunden.filter(k => k.plan === "pro" || k.plan === "Pro").length;
  const starterCount = kunden.filter(k => k.plan === "starter" || k.plan === "Starter").length;
  const noSub      = total - proCount - starterCount;
  const mrr        = (proCount * 499) + (starterCount * 249);  // Beispiel-Preise
  const avgMatches = total > 0 ? Math.round(kunden.reduce((s, k) => s + (k.matches_gesamt || 0), 0) / total) : 0;
  const branches   = {};
  kunden.forEach(k => { if (k.branche) branches[k.branche] = (branches[k.branche] || 0) + 1; });
  const topBranch  = Object.entries(branches).sort((a,b) => b[1]-a[1])[0];

  // Header
  const title = sheet.getRange("A1");
  title.setValue("📊 PublicFlow — KPI Dashboard");
  title.setFontSize(16).setFontWeight("bold").setFontFamily("Google Sans, Arial");
  sheet.setRowHeight(1, 45);

  // KPI-Blöcke
  const kpis = [
    ["👥 Gesamt-User",     total,                   ""],
    ["💎 Pro-Kunden",      proCount,                `${total > 0 ? Math.round(proCount/total*100) : 0}%`],
    ["🟢 Starter-Kunden",  starterCount,            `${total > 0 ? Math.round(starterCount/total*100) : 0}%`],
    ["⚪ Ohne Abo",        noSub,                   ""],
    ["💶 MRR (geschätzt)", `${mrr.toLocaleString("de-DE")} €`, ""],
    ["🎯 Ø Matches/User",  avgMatches,              ""],
    ["🏭 Top-Branche",     topBranch ? topBranch[0] : "–", topBranch ? `${topBranch[1]}x` : ""],
  ];

  const kpiRange = sheet.getRange(3, 1, kpis.length, 3);
  kpiRange.setValues(kpis);
  kpiRange.setFontSize(11).setFontFamily("Google Sans, Arial");

  // Header-Zeile für KPIs
  sheet.getRange("A2:C2").setValues([["Kennzahl", "Wert", "Anteil"]]);
  sheet.getRange("A2:C2").setBackground(COLORS.header).setFontColor("#ffffff").setFontWeight("bold");

  // KPI-Zellen formatieren
  kpis.forEach((_, i) => {
    const row = i + 3;
    sheet.getRange(row, 2).setFontWeight("bold").setFontSize(14);
    sheet.getRange(row, 1, 1, 3).setBackground(i % 2 === 0 ? COLORS.rowBase : COLORS.rowAlt);
    sheet.setRowHeight(row, 36);
  });

  // Spaltenbreiten
  sheet.setColumnWidth(1, 200);
  sheet.setColumnWidth(2, 180);
  sheet.setColumnWidth(3, 100);

  // Timestamp
  const tsRow = kpis.length + 5;
  sheet.getRange(tsRow, 1).setValue(`Stand: ${new Date().toLocaleString("de-DE")} · Automatisch via PublicFlow API`);
  sheet.getRange(tsRow, 1).setFontColor(COLORS.grey).setFontSize(9);

  Logger.log("✅ Stats Tab geschrieben");
}

// ═══════════════════════════════════════════════════════════════
//  HILFSFUNKTIONEN
// ═══════════════════════════════════════════════════════════════

// Lead-Score 0–100 berechnen
function calcLeadScore(k) {
  let score = 0;
  if (k.plan === "pro" || k.plan === "Pro")           score += 40;
  else if (k.plan === "starter" || k.plan === "Starter") score += 20;
  if (k.matches_gesamt > 10)  score += 20;
  else if (k.matches_gesamt > 0) score += 10;
  if (k.unternehmen)          score += 10;
  if (k.branche)              score += 10;
  if (k.keywords)             score += 10;
  if (k.min_budget > 0)       score += 5;
  if (k.max_budget > 50000)   score += 5;
  return Math.min(score, 100);
}

// Stage aus Daten ableiten
function getStage(k) {
  if (k.plan === "pro" || k.plan === "Pro")           return "✅ Kunde";
  if (k.plan === "starter" || k.plan === "Starter")   return "✅ Kunde";
  if (k.matches_gesamt > 0)                           return "🔥 Hot Lead";
  if (k.unternehmen || k.branche)                     return "📞 Kontaktiert";
  return "🆕 Neu";
}

// Stage-Zelle einfärben
function colorStage(cell, stage) {
  const map = {
    "🆕 Neu":          { bg: "#EFF6FF", fg: "#1D4ED8" },
    "📞 Kontaktiert":  { bg: "#FEF9C3", fg: "#92400E" },
    "🔥 Hot Lead":     { bg: "#FEF3C7", fg: "#B45309" },
    "✅ Kunde":        { bg: "#DCFCE7", fg: "#166534" },
    "❌ Verloren":     { bg: "#FEE2E2", fg: "#991B1B" },
  };
  const style = map[stage] || { bg: "#F3F4F6", fg: "#374151" };
  cell.setBackground(style.bg).setFontColor(style.fg).setFontWeight("bold");
}

// Toast-Nachricht
function showToast(ss, msg) {
  ss.toast(msg, "PublicFlow CRM Sync", 5);
}

// ═══════════════════════════════════════════════════════════════
//  MENÜ — erscheint in der Google-Sheets-Menüleiste
// ═══════════════════════════════════════════════════════════════
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🔵 PublicFlow")
    .addItem("🔄 Leads synchronisieren", "syncLeads")
    .addItem("📊 Stats aktualisieren",   "setupStatsTabOnly")
    .addSeparator()
    .addItem("⚙️ API-URL konfigurieren", "configureApiUrl")
    .addToUi();
}

function setupStatsTabOnly() {
  const data = fetchLeadsFromAPI();
  if (data && data.kunden) {
    setupStatsTab(SpreadsheetApp.getActiveSpreadsheet(), data.kunden);
    showToast(SpreadsheetApp.getActiveSpreadsheet(), "✅ Stats aktualisiert");
  }
}

function configureApiUrl() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.prompt(
    "⚙️ PublicFlow API-URL",
    "Gib die Railway-URL ein (z.B. https://publicflow-xxx.railway.app):",
    ui.ButtonSet.OK_CANCEL
  );
  if (result.getSelectedButton() === ui.Button.OK) {
    const url = result.getResponseText().trim();
    PropertiesService.getScriptProperties().setProperty("API_BASE", url);
    CONFIG.API_BASE = url;
    ui.alert(`✅ API-URL gespeichert:\n${url}`);
  }
}

// ═══════════════════════════════════════════════════════════════
//  AUTOMATISCHER TAGES-TRIGGER einrichten (einmalig ausführen)
// ═══════════════════════════════════════════════════════════════
function installDailyTrigger() {
  // Bestehende Trigger löschen
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === "syncLeads") ScriptApp.deleteTrigger(t);
  });

  // Täglich um 07:00 Uhr
  ScriptApp.newTrigger("syncLeads")
    .timeBased()
    .everyDays(1)
    .atHour(7)
    .create();

  SpreadsheetApp.getUi().alert("✅ Täglicher Trigger eingerichtet: syncLeads läuft täglich um 07:00 Uhr.");
}
